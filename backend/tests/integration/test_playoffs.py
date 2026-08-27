from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import UUID

from PIL import Image

from app.auth.roles import Role
from app.content.models import BanlistVersion
from app.matches.models import Match, MatchStage, MatchStatus, ResultSource
from app.registrations.models import Registration, RegistrationStatus, TournamentParticipant
from app.swiss.models import RankingSnapshot, SwissRound, SwissRoundStatus
from app.tournaments.models import Tournament, TournamentStatus


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def seed_ready_playoff(session_factory, make_user, *, playoff_size: int = 4):
    admin, admin_token = make_user(
        qq_number=f"940000{playoff_size:02d}", nickname=f"Top{playoff_size}管理员", role=Role.USER
    )
    players = [
        make_user(qq_number=f"94{playoff_size:02d}{index:04d}", nickname=f"种子{index}")
        for index in range(1, playoff_size + 1)
    ]
    with session_factory() as db:
        banlist = BanlistVersion(
            major_version=1,
            minor_version=0,
            title="淘汰赛测试禁卡表",
            content_html="<p>测试</p>",
            published_at=datetime.now(UTC),
            created_by_id=admin.id,
        )
        db.add(banlist)
        db.flush()
        tournament = Tournament(
            name=f"Phase 4 Top {playoff_size} 测试赛",
            description="固定种子签表验收",
            planned_start_at=datetime.now(UTC) + timedelta(days=1),
            max_players=playoff_size,
            swiss_rounds=1,
            playoff_size=playoff_size,
            banlist_version_id=banlist.id,
            status=TournamentStatus.SWISS.value,
            published_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            created_by_id=admin.id,
        )
        db.add(tournament)
        db.flush()
        participants: list[TournamentParticipant] = []
        participant_tokens: dict[UUID, str] = {}
        for user, token in players:
            registration = Registration(
                tournament_id=tournament.id,
                user_id=user.id,
                status=RegistrationStatus.APPROVED.value,
                reviewed_by_id=admin.id,
                reviewed_at=datetime.now(UTC),
            )
            db.add(registration)
            db.flush()
            participant = TournamentParticipant(
                tournament_id=tournament.id,
                user_id=user.id,
                registration_id=registration.id,
                nickname_snapshot=user.nickname,
            )
            db.add(participant)
            db.flush()
            participants.append(participant)
            participant_tokens[participant.id] = token
        swiss_round = SwissRound(
            tournament_id=tournament.id,
            round_no=1,
            status=SwissRoundStatus.COMPLETED.value,
            published_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db.add(swiss_round)
        db.flush()
        db.add(Match(
            tournament_id=tournament.id,
            swiss_round_id=swiss_round.id,
            stage=MatchStage.SWISS.value,
            round_no=1,
            table_no=1,
            player_a_id=participants[0].id,
            player_b_id=participants[1].id,
            winner_id=participants[0].id,
            status=MatchStatus.COMPLETED.value,
            result_source=ResultSource.ADMIN.value,
            result_locked=True,
        ))
        for rank, participant in enumerate(participants, start=1):
            db.add(RankingSnapshot(
                tournament_id=tournament.id,
                swiss_round_id=swiss_round.id,
                participant_id=participant.id,
                rank=rank,
                wins=playoff_size - rank,
                losses=rank - 1,
                omw=(playoff_size - rank) / playoff_size,
                loss_round_score=rank - 1,
            ))
        db.commit()
        return tournament.id, admin_token, participant_tokens


def generate_and_publish(client, tournament_id, admin_token):
    generated = client.post(
        f"/api/admin/tournaments/{tournament_id}/playoffs/generate", headers=auth(admin_token)
    )
    assert generated.status_code == 200, generated.json()
    assert generated.json()["status"] == "PUBLISHED"
    return generated.json(), generated.json()


def forfeit_all(client, round_data, admin_token):
    for match in round_data["matches"]:
        response = client.post(
            f"/api/admin/playoffs/matches/{match['id']}/forfeit",
            headers=auth(admin_token),
            json={"loser_id": match["player_b_id"], "reason": "测试账号无法继续参赛"},
        )
        assert response.status_code == 200, response.json()


def test_top_four_fixed_seeds_are_published_immediately(client, make_user, session_factory) -> None:
    tournament_id, admin_token, _ = seed_ready_playoff(session_factory, make_user, playoff_size=4)
    generated = client.post(
        f"/api/admin/tournaments/{tournament_id}/playoffs/generate", headers=auth(admin_token)
    )
    assert generated.status_code == 200
    assert generated.json()["status"] == "PUBLISHED"
    assert [(item["seed_a"], item["seed_b"]) for item in generated.json()["matches"]] == [(1, 4), (2, 3)]
    resolved = client.post(
        f"/api/admin/playoffs/matches/{generated.json()['matches'][0]['id']}/forfeit",
        headers=auth(admin_token),
        json={"loser_id": generated.json()["matches"][0]["player_b_id"]},
    )
    assert resolved.status_code == 200


def test_player_submissions_complete_playoff_match(client, make_user, session_factory) -> None:
    tournament_id, admin_token, tokens = seed_ready_playoff(session_factory, make_user, playoff_size=2)
    _, published = generate_and_publish(client, tournament_id, admin_token)
    match = published["matches"][0]
    swiss_history = client.get(
        f"/api/tournaments/{tournament_id}/matches/me",
        headers=auth(tokens[UUID(match["player_a_id"])]),
    )
    assert swiss_history.status_code == 200
    assert [(item["round_no"], item["table_no"], item["status"]) for item in swiss_history.json()] == [
        (1, 1, "COMPLETED")
    ]
    first = client.post(
        f"/api/playoffs/matches/{match['id']}/submissions",
        headers=auth(tokens[UUID(match["player_a_id"])]),
        json={"result": "WIN"},
    )
    second = client.post(
        f"/api/playoffs/matches/{match['id']}/submissions",
        headers=auth(tokens[UUID(match["player_b_id"])]),
        json={"result": "LOSS"},
    )
    assert first.json()["status"] == "WAITING"
    waiting_opponent_view = client.get(
        f"/api/tournaments/{tournament_id}/playoffs/matches/me",
        headers=auth(tokens[UUID(match["player_b_id"])]),
    ).json()
    assert waiting_opponent_view[0]["opponent_submitted"] is True
    assert waiting_opponent_view[0]["opponent_submission"] == "WIN"
    assert second.json()["status"] == "COMPLETED"
    overview = client.get(f"/api/tournaments/{tournament_id}/playoffs")
    assert overview.json()["awaiting_tournament_end"] is True
    assert overview.json()["champion_id"] == match["player_a_id"]
    # Phase 4 does not end the tournament automatically.
    assert client.get(f"/api/tournaments/{tournament_id}").json()["status"] == "ELIMINATION"


def test_admin_forfeit_overrides_conflicting_player_submissions(client, make_user, session_factory) -> None:
    tournament_id, admin_token, tokens = seed_ready_playoff(session_factory, make_user, playoff_size=2)
    _, published = generate_and_publish(client, tournament_id, admin_token)
    match = published["matches"][0]

    for participant_key in ("player_a_id", "player_b_id"):
        response = client.post(
            f"/api/playoffs/matches/{match['id']}/submissions",
            headers=auth(tokens[UUID(match[participant_key])]),
            json={"result": "WIN"},
        )
        assert response.status_code == 200
    assert response.json()["status"] == "CONFLICT"

    resolved = client.post(
        f"/api/admin/playoffs/matches/{match['id']}/forfeit",
        headers=auth(admin_token),
        json={"loser_id": match["player_b_id"]},
    )
    assert resolved.status_code == 200, resolved.json()
    assert resolved.json()["status"] == "COMPLETED"
    assert resolved.json()["result_source"] == "ADMIN"
    assert resolved.json()["winner_id"] == match["player_a_id"]
    assert resolved.json()["player_a_result"] == "WIN"
    assert resolved.json()["player_b_result"] == "LOSS"

    overview = client.get(
        f"/api/admin/tournaments/{tournament_id}/playoffs", headers=auth(admin_token)
    ).json()
    reloaded_match = overview["rounds"][0]["matches"][0]
    assert reloaded_match["player_a_result"] == "WIN"
    assert reloaded_match["player_b_result"] == "LOSS"


def test_next_stage_publication_locks_previous_results(client, make_user, session_factory) -> None:
    tournament_id, admin_token, _ = seed_ready_playoff(session_factory, make_user, playoff_size=4)
    _, semifinal = generate_and_publish(client, tournament_id, admin_token)
    forfeit_all(client, semifinal, admin_token)
    published_final = client.post(
        f"/api/admin/tournaments/{tournament_id}/playoffs/generate", headers=auth(admin_token)
    )
    assert published_final.status_code == 200
    assert published_final.json()["status"] == "PUBLISHED"

    # Generating the next fixed-seed stage publishes it immediately and locks prior results.
    correction_match = semifinal["matches"][0]
    locked = client.post(
        f"/api/admin/playoffs/matches/{correction_match['id']}/forfeit",
        headers=auth(admin_token),
        json={"loser_id": correction_match["player_a_id"]},
    )
    assert locked.status_code == 409
    assert locked.json()["code"] == "MATCH_RESULT_LOCKED"


def test_top_eight_progresses_through_all_stages(client, make_user, session_factory) -> None:
    tournament_id, admin_token, _ = seed_ready_playoff(session_factory, make_user, playoff_size=8)
    _, quarterfinal = generate_and_publish(client, tournament_id, admin_token)
    assert [(item["seed_a"], item["seed_b"]) for item in quarterfinal["matches"]] == [
        (1, 8), (4, 5), (2, 7), (3, 6)
    ]
    forfeit_all(client, quarterfinal, admin_token)
    _, semifinal = generate_and_publish(client, tournament_id, admin_token)
    assert semifinal["name"] == "半决赛"
    forfeit_all(client, semifinal, admin_token)
    _, final = generate_and_publish(client, tournament_id, admin_token)
    assert final["name"] == "决赛"
    forfeit_all(client, final, admin_token)
    overview = client.get(f"/api/tournaments/{tournament_id}/playoffs").json()
    assert overview["awaiting_tournament_end"] is True
    assert len(overview["rounds"]) == 3


def test_phase5_end_decks_and_immutable_weekly_report(client, make_user, session_factory) -> None:
    tournament_id, admin_token, tokens = seed_ready_playoff(session_factory, make_user, playoff_size=8)
    admin_headers = auth(admin_token)
    _, quarterfinal = generate_and_publish(client, tournament_id, admin_token)
    forfeit_all(client, quarterfinal, admin_token)
    _, semifinal = generate_and_publish(client, tournament_id, admin_token)
    forfeit_all(client, semifinal, admin_token)
    _, final = generate_and_publish(client, tournament_id, admin_token)
    forfeit_all(client, final, admin_token)

    ended = client.post(f"/api/admin/tournaments/{tournament_id}/end", headers=admin_headers)
    assert ended.status_code == 200, ended.json()
    assert ended.json()["status"] == "ENDED"
    assert ended.json()["ended_at"] is not None

    locked = client.post(
        f"/api/admin/playoffs/matches/{final['matches'][0]['id']}/forfeit",
        headers=admin_headers,
        json={"loser_id": final["matches"][0]["player_a_id"], "reason": "结束后尝试修改"},
    )
    assert locked.status_code == 409
    assert locked.json()["code"] == "MATCH_RESULT_LOCKED"

    submissions = client.get(
        f"/api/admin/tournaments/{tournament_id}/deck-submissions", headers=admin_headers
    ).json()
    assert len(submissions["items"]) == 4
    assert [item["placement"] for item in submissions["items"]] == [1, 2, 3, 4]
    assert submissions["approved_count"] == 0

    non_finalist_id = next(item for item in tokens if item not in {
        UUID(submission["participant_id"]) for submission in submissions["items"]
    })
    denied = client.post(
        f"/api/tournaments/{tournament_id}/deck-submission",
        headers=auth(tokens[non_finalist_id]),
        files={"image": ("deck.png", b"not-an-image", "image/png")},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "NOT_FINAL_FOUR"

    image_buffer = BytesIO()
    Image.new("RGB", (24, 16), color=(141, 61, 45)).save(image_buffer, format="PNG")
    image_bytes = image_buffer.getvalue()
    for index, submission in enumerate(submissions["items"]):
        participant_id = UUID(submission["participant_id"])
        uploaded = client.post(
            f"/api/tournaments/{tournament_id}/deck-submission",
            headers=auth(tokens[participant_id]),
            files={"image": (f"deck-{index}.png", image_bytes, "image/png")},
        )
        assert uploaded.status_code == 200, uploaded.json()
        assert uploaded.json()["status"] == "PENDING_REVIEW"
        if index == 0:
            returned = client.post(
                f"/api/admin/deck-submissions/{submission['id']}/return",
                headers=admin_headers,
                json={"reason": ""},
            )
            assert returned.status_code == 200, returned.json()
            assert returned.json()["status"] == "REUPLOAD_REQUIRED"
            assert returned.json()["review_note"] == ""
            reuploaded = client.post(
                f"/api/tournaments/{tournament_id}/deck-submission",
                headers=auth(tokens[participant_id]),
                files={"image": ("deck-fixed.png", image_bytes, "image/png")},
            )
            assert reuploaded.json()["status"] == "PENDING_REVIEW"

        before_approval = client.post(
            f"/api/admin/tournaments/{tournament_id}/reports/generate", headers=admin_headers
        )
        assert before_approval.status_code == 409
        assert before_approval.json()["code"] == "DECK_APPROVALS_INCOMPLETE"

        approved = client.post(
            f"/api/admin/deck-submissions/{submission['id']}/approve", headers=admin_headers
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "APPROVED"

    approved_reupload = client.post(
        f"/api/tournaments/{tournament_id}/deck-submission",
        headers=auth(tokens[UUID(submissions['items'][0]['participant_id'])]),
        files={"image": ("replace.png", image_bytes, "image/png")},
    )
    assert approved_reupload.status_code == 409
    assert approved_reupload.json()["code"] == "DECK_SUBMISSION_LOCKED"

    generated = client.post(
        f"/api/admin/tournaments/{tournament_id}/reports/generate", headers=admin_headers
    )
    assert generated.status_code == 200, generated.json()
    assert generated.json()["status"] == "PUBLISHED"
    assert generated.json()["published_at"] is not None
    snapshot = generated.json()["snapshot_content"]
    assert snapshot["template_version"] == 2
    assert len(snapshot["podium"]) == 4
    assert snapshot["tournament"]["format"] == "BO1"
    assert "swiss_rankings" not in snapshot
    assert "playoff_rounds" not in snapshot
    assert client.get("/api/reports").json()["total"] == 1
    assert client.get(f"/api/reports/{generated.json()['id']}").status_code == 200

    player_forbidden = client.post(
        f"/api/admin/reports/{generated.json()['id']}/publish",
        headers=auth(next(iter(tokens.values()))),
    )
    assert player_forbidden.status_code == 403

    regenerate = client.post(
        f"/api/admin/tournaments/{tournament_id}/reports/generate", headers=admin_headers
    )
    republish = client.post(
        f"/api/admin/reports/{generated.json()['id']}/publish", headers=admin_headers
    )
    assert regenerate.status_code == 409
    assert regenerate.json()["code"] == "REPORT_PUBLISHED"
    assert republish.status_code == 409
    assert republish.json()["code"] == "REPORT_ALREADY_PUBLISHED"
