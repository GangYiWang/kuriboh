from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.auth.roles import Role
from app.content.models import BanlistVersion
from app.matches.models import Match
from app.registrations.models import Registration, RegistrationStatus, TournamentParticipant
from app.tournaments.models import Tournament, TournamentStatus


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def seed_swiss_tournament(session_factory, make_user, *, player_count: int = 4, swiss_rounds: int = 3):
    admin, admin_token = make_user(
        qq_number="91000000", nickname="瑞士轮管理员", role=Role.TOURNAMENT_ADMIN
    )
    players = [
        make_user(qq_number=f"9100000{index + 1}", nickname=f"瑞士选手{index + 1}")
        for index in range(player_count)
    ]
    with session_factory() as db:
        banlist = BanlistVersion(
            major_version=1,
            minor_version=0,
            title="瑞士轮测试禁卡表",
            content_html="<p>测试</p>",
            published_at=datetime.now(UTC),
            created_by_id=admin.id,
        )
        db.add(banlist)
        db.flush()
        tournament = Tournament(
            name="Phase 3 瑞士轮测试赛",
            description="瑞士轮核心验收",
            planned_start_at=datetime.now(UTC) + timedelta(days=1),
            max_players=max(2, player_count),
            swiss_rounds=swiss_rounds,
            playoff_size=2,
            banlist_version_id=banlist.id,
            status=TournamentStatus.SWISS.value,
            published_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            created_by_id=admin.id,
        )
        db.add(tournament)
        db.flush()
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
            participant_tokens[participant.id] = token
        db.commit()
        return tournament.id, admin_token, participant_tokens


def generate_and_publish(client, tournament_id, admin_token, *, seed: int = 7):
    generated = client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/generate",
        headers=auth(admin_token),
        json={"seed": seed},
    )
    assert generated.status_code == 200, generated.json()
    round_id = generated.json()["id"]
    published = client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/{round_id}/publish",
        headers=auth(admin_token),
    )
    assert published.status_code == 200, published.json()
    return published.json()


def submit_for_match(client, match, participant_tokens, a_result: str, b_result: str | None = None):
    first = client.post(
        f"/api/matches/{match['id']}/submissions",
        headers=auth(participant_tokens[UUID(match["player_a_id"])]),
        json={"result": a_result},
    )
    assert first.status_code == 200, first.json()
    if b_result is None:
        return first, None
    second = client.post(
        f"/api/matches/{match['id']}/submissions",
        headers=auth(participant_tokens[UUID(match["player_b_id"])]),
        json={"result": b_result},
    )
    assert second.status_code == 200, second.json()
    return first, second


def test_odd_first_round_has_completed_bye_and_can_regenerate_preview(client, make_user, session_factory) -> None:
    tournament_id, admin_token, _ = seed_swiss_tournament(session_factory, make_user, player_count=5)
    first = client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/generate",
        headers=auth(admin_token),
        json={"seed": 11},
    )
    regenerated = client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/regenerate",
        headers=auth(admin_token),
        json={"seed": 12},
    )
    assert first.status_code == regenerated.status_code == 200
    assert first.json()["status"] == regenerated.json()["status"] == "DRAFT"
    assert sum(item["player_b_id"] is None for item in regenerated.json()["matches"]) == 1

    draft_match = next(item for item in regenerated.json()["matches"] if item["player_b_id"])
    draft_resolution = client.post(
        f"/api/admin/matches/{draft_match['id']}/resolve",
        headers=auth(admin_token),
        json={"winner_id": draft_match["player_a_id"]},
    )
    assert draft_resolution.status_code == 409
    assert draft_resolution.json()["code"] == "MATCH_NOT_PUBLISHED"

    ids = [
        participant_id
        for match in regenerated.json()["matches"]
        for participant_id in (match["player_a_id"], match["player_b_id"])
        if participant_id
    ]
    swapped = client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/{regenerated.json()['id']}/swap",
        headers=auth(admin_token),
        json={"first_participant_id": ids[0], "second_participant_id": ids[-1]},
    )
    assert swapped.status_code == 200
    assert swapped.json()["matches"] != regenerated.json()["matches"]

    published = client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/{swapped.json()['id']}/publish",
        headers=auth(admin_token),
    )
    bye = next(item for item in published.json()["matches"] if item["player_b_id"] is None)
    assert bye["status"] == "COMPLETED"
    assert bye["winner_id"] == bye["player_a_id"]
    assert bye["result_source"] == "BYE"


@pytest.mark.parametrize(
    ("a_result", "b_result", "expected_status", "winner_slot"),
    [
        ("WIN", "LOSS", "COMPLETED", "player_a_id"),
        ("LOSS", "WIN", "COMPLETED", "player_b_id"),
        ("WIN", "WIN", "CONFLICT", None),
        ("LOSS", "LOSS", "CONFLICT", None),
    ],
)
def test_all_four_submission_combinations(
    client, make_user, session_factory, a_result, b_result, expected_status, winner_slot
) -> None:
    tournament_id, admin_token, participant_tokens = seed_swiss_tournament(
        session_factory, make_user, player_count=2, swiss_rounds=1
    )
    match = generate_and_publish(client, tournament_id, admin_token)["matches"][0]
    _, second = submit_for_match(client, match, participant_tokens, a_result, b_result)
    assert second.json()["status"] == expected_status
    assert second.json()["winner_id"] == (match[winner_slot] if winner_slot else None)


def test_waiting_match_can_be_resolved_by_admin(client, make_user, session_factory) -> None:
    tournament_id, admin_token, _ = seed_swiss_tournament(
        session_factory, make_user, player_count=2, swiss_rounds=1
    )
    match = generate_and_publish(client, tournament_id, admin_token)["matches"][0]

    resolved = client.post(
        f"/api/admin/matches/{match['id']}/resolve",
        headers=auth(admin_token),
        json={"winner_id": match["player_a_id"]},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "COMPLETED"
    assert resolved.json()["result_source"] == "ADMIN"

    audit = client.get(
        f"/api/admin/audit-logs?tournament_id={tournament_id}&action_type=SWISS_MATCH_RESOLVED",
        headers=auth(admin_token),
    )
    assert audit.status_code == 200
    resolution_log = next(item for item in audit.json()["items"] if item["target_id"] == match["id"])
    assert resolution_log["after_json"]["winner_id"] == match["player_a_id"]
    assert resolution_log["after_json"]["reason"] is None


def test_independent_submissions_conflict_resolution_and_ranking_snapshot(client, make_user, session_factory) -> None:
    tournament_id, admin_token, participant_tokens = seed_swiss_tournament(session_factory, make_user)
    round_data = generate_and_publish(client, tournament_id, admin_token)
    first_match, second_match = round_data["matches"]

    first_submission, _ = submit_for_match(client, first_match, participant_tokens, "WIN")
    assert first_submission.json()["status"] == "WAITING"
    assert first_submission.json()["opponent_submitted"] is False
    assert first_submission.json()["opponent_submission"] is None
    opponent_view = client.get(
        f"/api/tournaments/{tournament_id}/matches/me",
        headers=auth(participant_tokens[UUID(first_match["player_b_id"])]),
    ).json()
    opponent_match = next(item for item in opponent_view if item["id"] == first_match["id"])
    assert opponent_match["opponent_submitted"] is True
    assert opponent_match["opponent_submission"] == "WIN"
    _, agreed = submit_for_match(client, first_match, participant_tokens, "WIN", "LOSS")
    assert agreed.json()["status"] == "COMPLETED"
    assert agreed.json()["winner_id"] == first_match["player_a_id"]

    _, conflict = submit_for_match(client, second_match, participant_tokens, "WIN", "WIN")
    assert conflict.json()["status"] == "CONFLICT"
    resolved = client.post(
        f"/api/admin/matches/{second_match['id']}/resolve",
        headers=auth(admin_token),
        json={"winner_id": second_match["player_b_id"]},
    )
    assert resolved.status_code == 200
    assert resolved.json()["result_source"] == "ADMIN"

    overview = client.get(f"/api/tournaments/{tournament_id}/swiss")
    assert overview.status_code == 200
    assert overview.json()["completed_rounds"] == 1
    assert overview.json()["ranking_round_no"] == 1
    assert len(overview.json()["rankings"]) == 4


def test_preview_does_not_lock_previous_result_but_publish_does(client, make_user, session_factory) -> None:
    tournament_id, admin_token, participant_tokens = seed_swiss_tournament(session_factory, make_user)
    round_one = generate_and_publish(client, tournament_id, admin_token)
    for match in round_one["matches"]:
        submit_for_match(client, match, participant_tokens, "WIN", "LOSS")

    preview = client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/generate",
        headers=auth(admin_token),
        json={"seed": 19},
    )
    old_match = round_one["matches"][0]
    correction = client.post(
        f"/api/admin/matches/{old_match['id']}/resolve",
        headers=auth(admin_token),
        json={"winner_id": old_match["player_b_id"]},
    )
    assert correction.status_code == 200
    # Correcting a completed result invalidates the stale next-round preview.
    rounds_after_correction = client.get(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds", headers=auth(admin_token)
    )
    assert len(rounds_after_correction.json()) == 1

    preview = client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/generate",
        headers=auth(admin_token),
        json={"seed": 20},
    )
    client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/{preview.json()['id']}/publish",
        headers=auth(admin_token),
    )
    locked = client.post(
        f"/api/admin/matches/{old_match['id']}/resolve",
        headers=auth(admin_token),
        json={"winner_id": old_match["player_a_id"]},
    )
    assert locked.status_code == 409
    assert locked.json()["code"] == "MATCH_RESULT_LOCKED"


def test_swap_and_publish_reject_historical_rematches(client, make_user, session_factory) -> None:
    tournament_id, admin_token, participant_tokens = seed_swiss_tournament(session_factory, make_user)
    round_one = generate_and_publish(client, tournament_id, admin_token)
    for match in round_one["matches"]:
        submit_for_match(client, match, participant_tokens, "WIN", "LOSS")

    preview = client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/generate",
        headers=auth(admin_token),
        json={"seed": 41},
    ).json()
    previous_pair = round_one["matches"][0]
    player_a_id = previous_pair["player_a_id"]
    player_b_id = previous_pair["player_b_id"]
    player_a_match = next(
        item for item in preview["matches"] if player_a_id in {item["player_a_id"], item["player_b_id"]}
    )
    player_a_opponent_id = (
        player_a_match["player_b_id"]
        if player_a_match["player_a_id"] == player_a_id
        else player_a_match["player_a_id"]
    )

    rejected_swap = client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/{preview['id']}/swap",
        headers=auth(admin_token),
        json={
            "first_participant_id": player_a_opponent_id,
            "second_participant_id": player_b_id,
        },
    )
    assert rejected_swap.status_code == 400
    assert rejected_swap.json()["code"] == "INVALID_PAIRING_DRAFT"
    assert "存在重复对手" in rejected_swap.json()["details"]["errors"]

    participant_ids = {
        participant_id
        for match in preview["matches"]
        for participant_id in (match["player_a_id"], match["player_b_id"])
        if participant_id
    }
    remaining_ids = participant_ids - {player_a_id, player_b_id}
    with session_factory() as db:
        first_match = db.get(Match, UUID(preview["matches"][0]["id"]))
        second_match = db.get(Match, UUID(preview["matches"][1]["id"]))
        first_match.player_a_id = UUID(player_a_id)
        first_match.player_b_id = UUID(player_b_id)
        second_match.player_a_id, second_match.player_b_id = map(UUID, remaining_ids)
        db.commit()

    rejected_publish = client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/{preview['id']}/publish",
        headers=auth(admin_token),
    )
    assert rejected_publish.status_code == 400
    assert rejected_publish.json()["code"] == "INVALID_PAIRING_DRAFT"
    assert "存在重复对手" in rejected_publish.json()["details"]["errors"]


def test_withdrawal_discards_unpublished_preview(client, make_user, session_factory) -> None:
    tournament_id, admin_token, participant_tokens = seed_swiss_tournament(session_factory, make_user)
    round_one = generate_and_publish(client, tournament_id, admin_token)
    for match in round_one["matches"]:
        submit_for_match(client, match, participant_tokens, "WIN", "LOSS")
    preview = client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/generate",
        headers=auth(admin_token),
        json={"seed": 31},
    )
    assert preview.status_code == 200
    participant_id = next(iter(participant_tokens))
    withdrawn = client.post(
        f"/api/admin/tournaments/{tournament_id}/participants/{participant_id}/withdraw",
        headers=auth(admin_token),
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["after_round_no"] == 1
    rounds = client.get(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds", headers=auth(admin_token)
    )
    assert len(rounds.json()) == 1
