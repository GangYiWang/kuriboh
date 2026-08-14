from uuid import UUID

import pytest

from app.playoffs.algorithm import SeededParticipant, fixed_seed_order, generate_playoff_bracket


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (2, [(1, 2)]),
        (4, [(1, 4), (2, 3)]),
        (8, [(1, 8), (4, 5), (2, 7), (3, 6)]),
    ],
)
def test_fixed_seed_bracket_paths(size: int, expected: list[tuple[int, int]]) -> None:
    participants = [SeededParticipant(seed, UUID(int=seed)) for seed in range(1, size + 1)]
    pairings = generate_playoff_bracket(participants)
    assert [(item.player_a.seed, item.player_b.seed) for item in pairings] == expected
    assert fixed_seed_order(size) == [seed for pair in expected for seed in pair]


def test_playoff_size_must_be_a_power_of_two() -> None:
    with pytest.raises(ValueError):
        fixed_seed_order(6)
