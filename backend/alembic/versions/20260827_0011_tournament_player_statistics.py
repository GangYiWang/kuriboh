"""Add tournament settlement results and player statistics.

Revision ID: 20260827_0011
Revises: 20260825_0010
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "20260827_0011"
down_revision: str | None = "20260825_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "player_statistics",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tournament_count", sa.Integer(), nullable=False),
        sa.Column("total_points", sa.Integer(), nullable=False),
        sa.Column("champion_count", sa.Integer(), nullable=False),
        sa.Column("runner_up_count", sa.Integer(), nullable=False),
        sa.Column("top_4_count", sa.Integer(), nullable=False),
        sa.Column("top_8_count", sa.Integer(), nullable=False),
        sa.Column("total_wins", sa.Integer(), nullable=False),
        sa.Column("total_losses", sa.Integer(), nullable=False),
        sa.Column("total_byes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "tournament_count >= 0 and total_points >= 0 and champion_count >= 0 "
            "and runner_up_count >= 0 and top_4_count >= 0 and top_8_count >= 0 "
            "and total_wins >= 0 and total_losses >= 0 and total_byes >= 0",
            name="ck_player_statistics_nonnegative",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "tournament_player_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("participant_status", sa.String(length=24), nullable=False),
        sa.Column("finish_level", sa.String(length=24), nullable=False),
        sa.Column("placement", sa.Integer(), nullable=True),
        sa.Column("swiss_rank", sa.Integer(), nullable=True),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("losses", sa.Integer(), nullable=False),
        sa.Column("bye_count", sa.Integer(), nullable=False),
        sa.Column("points_awarded", sa.Integer(), nullable=False),
        sa.Column("points_rule_version", sa.Integer(), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "participant_status in ('ACTIVE', 'WITHDRAWN')",
            name="ck_result_participant_status",
        ),
        sa.CheckConstraint(
            "finish_level in ('PARTICIPATED', 'TOP_8', 'TOP_4', 'RUNNER_UP', 'CHAMPION')",
            name="ck_result_finish_level",
        ),
        sa.CheckConstraint("placement is null or placement between 1 and 4", name="ck_result_placement"),
        sa.CheckConstraint("swiss_rank is null or swiss_rank >= 1", name="ck_result_swiss_rank"),
        sa.CheckConstraint("wins >= 0 and losses >= 0 and bye_count >= 0", name="ck_result_record"),
        sa.CheckConstraint("points_awarded >= 0", name="ck_result_points"),
        sa.CheckConstraint("points_rule_version >= 1", name="ck_result_points_rule_version"),
        sa.ForeignKeyConstraint(["participant_id"], ["tournament_participants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", "participant_id", name="uq_result_tournament_participant"),
        sa.UniqueConstraint("tournament_id", "placement", name="uq_result_tournament_placement"),
        sa.UniqueConstraint("tournament_id", "user_id", name="uq_result_tournament_user"),
    )
    op.create_index(
        "ix_results_tournament_placement",
        "tournament_player_results",
        ["tournament_id", "placement"],
    )
    op.create_index(
        "ix_results_user_settled",
        "tournament_player_results",
        ["user_id", "settled_at"],
    )
    _backfill_existing_tournaments()


def _backfill_existing_tournaments() -> None:
    connection = op.get_bind()
    tournaments = list(connection.execute(sa.text(
        "SELECT id, ended_at FROM tournaments WHERE status = 'ENDED' ORDER BY ended_at, id"
    )).mappings())
    statistics: dict[object, dict[str, int]] = {}

    for tournament in tournaments:
        tournament_id = tournament["id"]
        settled_at = tournament["ended_at"] or datetime.now(UTC)
        participants = list(connection.execute(sa.text(
            "SELECT id, user_id, status, bye_count FROM tournament_participants "
            "WHERE tournament_id = :tournament_id ORDER BY user_id"
        ), {"tournament_id": tournament_id}).mappings())
        placements = {
            row["participant_id"]: row["placement"]
            for row in connection.execute(sa.text(
                "SELECT participant_id, placement FROM deck_submissions "
                "WHERE tournament_id = :tournament_id"
            ), {"tournament_id": tournament_id}).mappings()
        }
        top_eight_losers = {
            row["loser_id"]
            for row in connection.execute(sa.text(
                "SELECT CASE WHEN match_item.winner_id = match_item.player_a_id "
                "THEN match_item.player_b_id ELSE match_item.player_a_id END AS loser_id "
                "FROM matches AS match_item "
                "JOIN playoff_rounds AS round_item ON round_item.id = match_item.playoff_round_id "
                "WHERE round_item.tournament_id = :tournament_id AND round_item.bracket_size = 8 "
                "AND round_item.status = 'COMPLETED' AND match_item.status = 'COMPLETED' "
                "AND match_item.player_b_id IS NOT NULL AND match_item.winner_id IS NOT NULL"
            ), {"tournament_id": tournament_id}).mappings()
        }
        swiss_ranks = {
            row["participant_id"]: row["rank"]
            for row in connection.execute(sa.text(
                "SELECT ranking.participant_id, ranking.rank "
                "FROM ranking_snapshots AS ranking "
                "JOIN swiss_rounds AS round_item ON round_item.id = ranking.swiss_round_id "
                "WHERE round_item.tournament_id = :tournament_id AND round_item.status = 'COMPLETED' "
                "AND round_item.round_no = (SELECT MAX(latest.round_no) FROM swiss_rounds AS latest "
                "WHERE latest.tournament_id = :tournament_id AND latest.status = 'COMPLETED')"
            ), {"tournament_id": tournament_id}).mappings()
        }
        wins: dict[object, int] = {}
        losses: dict[object, int] = {}
        matches = connection.execute(sa.text(
            "SELECT player_a_id, player_b_id, winner_id FROM matches "
            "WHERE tournament_id = :tournament_id AND status = 'COMPLETED' "
            "AND player_b_id IS NOT NULL AND winner_id IS NOT NULL"
        ), {"tournament_id": tournament_id}).mappings()
        for match in matches:
            winner_id = match["winner_id"]
            loser_id = match["player_b_id"] if winner_id == match["player_a_id"] else match["player_a_id"]
            wins[winner_id] = wins.get(winner_id, 0) + 1
            losses[loser_id] = losses.get(loser_id, 0) + 1

        result_values: list[dict[str, object]] = []
        for participant in participants:
            participant_id = participant["id"]
            placement = placements.get(participant_id)
            if placement == 1:
                finish_level, points = "CHAMPION", 8
            elif placement == 2:
                finish_level, points = "RUNNER_UP", 4
            elif placement in {3, 4}:
                finish_level, points = "TOP_4", 2
            elif participant_id in top_eight_losers:
                finish_level, points = "TOP_8", 1
            else:
                finish_level, points = "PARTICIPATED", 0
            result_values.append({
                "id": uuid4(),
                "tournament_id": tournament_id,
                "participant_id": participant_id,
                "user_id": participant["user_id"],
                "participant_status": participant["status"],
                "finish_level": finish_level,
                "placement": placement,
                "swiss_rank": swiss_ranks.get(participant_id),
                "wins": wins.get(participant_id, 0),
                "losses": losses.get(participant_id, 0),
                "bye_count": participant["bye_count"],
                "points_awarded": points,
                "points_rule_version": 1,
                "settled_at": settled_at,
            })
            totals = statistics.setdefault(participant["user_id"], {
                "tournament_count": 0,
                "total_points": 0,
                "champion_count": 0,
                "runner_up_count": 0,
                "top_4_count": 0,
                "top_8_count": 0,
                "total_wins": 0,
                "total_losses": 0,
                "total_byes": 0,
            })
            totals["tournament_count"] += 1
            totals["total_points"] += points
            totals["champion_count"] += int(finish_level == "CHAMPION")
            totals["runner_up_count"] += int(finish_level == "RUNNER_UP")
            totals["top_4_count"] += int(finish_level in {"TOP_4", "RUNNER_UP", "CHAMPION"})
            totals["top_8_count"] += int(finish_level in {"TOP_8", "TOP_4", "RUNNER_UP", "CHAMPION"})
            totals["total_wins"] += wins.get(participant_id, 0)
            totals["total_losses"] += losses.get(participant_id, 0)
            totals["total_byes"] += participant["bye_count"]

        if result_values:
            connection.execute(sa.text(
                "INSERT INTO tournament_player_results "
                "(id, tournament_id, participant_id, user_id, participant_status, finish_level, "
                "placement, swiss_rank, wins, losses, bye_count, points_awarded, points_rule_version, settled_at) "
                "VALUES (:id, :tournament_id, :participant_id, :user_id, :participant_status, :finish_level, "
                ":placement, :swiss_rank, :wins, :losses, :bye_count, :points_awarded, :points_rule_version, :settled_at)"
            ), result_values)

    if statistics:
        connection.execute(sa.text(
            "INSERT INTO player_statistics "
            "(user_id, tournament_count, total_points, champion_count, runner_up_count, top_4_count, "
            "top_8_count, total_wins, total_losses, total_byes) "
            "VALUES (:user_id, :tournament_count, :total_points, :champion_count, :runner_up_count, "
            ":top_4_count, :top_8_count, :total_wins, :total_losses, :total_byes)"
        ), [dict(user_id=user_id, **totals) for user_id, totals in statistics.items()])


def downgrade() -> None:
    op.drop_index("ix_results_user_settled", table_name="tournament_player_results")
    op.drop_index("ix_results_tournament_placement", table_name="tournament_player_results")
    op.drop_table("tournament_player_results")
    op.drop_table("player_statistics")
