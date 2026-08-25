from itertools import combinations
from random import Random
from uuid import UUID

import pytest

from app.swiss.algorithm import (
    MatchRecord,
    Pairing,
    PairingUnavailableError,
    StandingInput,
    calculate_rankings,
    generate_swiss_pairings,
    validate_pairing_draft,
)


def player(number: int, *, wins: int = 0, rank: int | None = None, bye_count: int = 0) -> StandingInput:
    return StandingInput(
        participant_id=UUID(int=number),
        nickname=f"P{number:02d}",
        wins=wins,
        rank=rank or number,
        bye_count=bye_count,
    )


def test_first_round_even_and_odd_fields_are_complete_and_repeatable() -> None:
    even = generate_swiss_pairings([player(i) for i in range(1, 7)], set(), Random(17))
    repeated = generate_swiss_pairings([player(i) for i in range(1, 7)], set(), Random(17))
    assert even == repeated
    assert len(even) == 3
    assert {item.player_a_id for item in even} | {item.player_b_id for item in even} == {
        UUID(int=i) for i in range(1, 7)
    }

    odd = generate_swiss_pairings([player(i) for i in range(1, 6)], set(), Random(17))
    assert len(odd) == 3
    assert sum(item.player_b_id is None for item in odd) == 1


def test_bye_prefers_a_player_without_a_previous_bye() -> None:
    players = [player(1, bye_count=1), player(2), player(3, wins=1)]
    pairings = generate_swiss_pairings(players, set(), Random(4))
    bye = next(item for item in pairings if item.player_b_id is None)
    assert bye.player_a_id == UUID(int=2)


def test_later_round_avoids_repeats_before_same_score_pairing() -> None:
    players = [player(1, wins=1), player(2, wins=1), player(3), player(4)]
    prior = {frozenset((UUID(int=1), UUID(int=2))), frozenset((UUID(int=3), UUID(int=4)))}
    pairings = generate_swiss_pairings(players, prior, Random(8))
    assert all(
        frozenset((item.player_a_id, item.player_b_id)) not in prior
        for item in pairings
        if item.player_b_id is not None
    )
    assert any("跨胜场组" in item.warnings for item in pairings)


def test_odd_score_group_downfloats_one_player() -> None:
    players = [player(1, wins=2), player(2, wins=2), player(3, wins=2), player(4, wins=1)]
    pairings = generate_swiss_pairings(players, set(), Random(3))
    assert sum("跨胜场组" in item.warnings for item in pairings) == 1


def test_large_field_uses_global_non_repeating_matching() -> None:
    players = [player(index) for index in range(1, 23)]
    allowed = {
        frozenset((UUID(int=index), UUID(int=(index % 22) + 1)))
        for index in range(1, 23)
    }
    prior = {
        frozenset((left.participant_id, right.participant_id))
        for left, right in combinations(players, 2)
        if frozenset((left.participant_id, right.participant_id)) not in allowed
    }

    pairings = generate_swiss_pairings(players, prior, Random(21))

    assert len(pairings) == 11
    assert all(
        frozenset((item.player_a_id, item.player_b_id)) not in prior
        for item in pairings
        if item.player_b_id is not None
    )


def test_same_score_pairs_are_preferred_after_repeat_edges_are_removed() -> None:
    players = [
        player(1, wins=2),
        player(2, wins=2),
        player(3, wins=2),
        player(4, wins=2),
        player(5, wins=1),
        player(6, wins=1),
    ]

    pairings = generate_swiss_pairings(players, set(), Random(9))

    assert all("跨胜场组" not in item.warnings for item in pairings)


def test_pairing_fails_instead_of_reusing_an_opponent() -> None:
    players = [player(index) for index in range(1, 5)]
    isolated_player = UUID(int=4)
    prior = {
        frozenset((isolated_player, UUID(int=index)))
        for index in range(1, 4)
    }

    with pytest.raises(PairingUnavailableError):
        generate_swiss_pairings(players, prior, Random(2))


def test_draft_validation_rejects_historical_rematches() -> None:
    pairings = [Pairing(UUID(int=1), UUID(int=2)), Pairing(UUID(int=3), UUID(int=4))]
    errors = validate_pairing_draft(
        pairings,
        {UUID(int=index) for index in range(1, 5)},
        {frozenset((UUID(int=1), UUID(int=2)))},
    )

    assert "存在重复对手" in errors


def test_bye_is_a_win_but_not_an_omw_opponent() -> None:
    players = [player(1), player(2), player(3)]
    matches = [
        MatchRecord(1, UUID(int=1), None, UUID(int=1)),
        MatchRecord(1, UUID(int=2), UUID(int=3), UUID(int=2)),
    ]
    ranking = {item.participant_id: item for item in calculate_rankings(players, matches)}
    assert ranking[UUID(int=1)].wins == 1
    assert ranking[UUID(int=1)].omw == 0
    assert ranking[UUID(int=3)].omw == 1


def test_ranking_chain_uses_loss_round_score_head_to_head_and_nickname_stably() -> None:
    players = [
        StandingInput(UUID(int=1), "Alpha"),
        StandingInput(UUID(int=2), "Bravo"),
        StandingInput(UUID(int=3), "Charlie"),
        StandingInput(UUID(int=4), "Delta"),
    ]
    matches = [
        MatchRecord(1, UUID(int=1), UUID(int=2), UUID(int=1)),
        MatchRecord(1, UUID(int=3), UUID(int=4), UUID(int=3)),
        MatchRecord(2, UUID(int=1), UUID(int=3), UUID(int=3)),
        MatchRecord(2, UUID(int=2), UUID(int=4), UUID(int=2)),
    ]
    first = calculate_rankings(players, matches)
    second = calculate_rankings(players, matches)
    assert first == second
    assert [item.nickname for item in first] == ["Charlie", "Alpha", "Bravo", "Delta"]
    assert first[1].loss_round_score == 4
    assert first[2].loss_round_score == 1
