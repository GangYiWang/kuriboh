from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class SeededParticipant:
    seed: int
    participant_id: UUID


@dataclass(frozen=True)
class SeededPairing:
    player_a: SeededParticipant
    player_b: SeededParticipant


def fixed_seed_order(size: int) -> list[int]:
    if size < 2 or size & (size - 1):
        raise ValueError("playoff size must be a power of two")
    order = [1, 2]
    current_size = 2
    while current_size < size:
        next_size = current_size * 2
        order = [value for seed in order for value in (seed, next_size + 1 - seed)]
        current_size = next_size
    return order


def generate_playoff_bracket(participants: list[SeededParticipant]) -> list[SeededPairing]:
    size = len(participants)
    order = fixed_seed_order(size)
    by_seed = {item.seed: item for item in participants}
    if set(by_seed) != set(range(1, size + 1)):
        raise ValueError("playoff seeds must be contiguous from one")
    ordered = [by_seed[seed] for seed in order]
    return [SeededPairing(ordered[index], ordered[index + 1]) for index in range(0, size, 2)]


def playoff_stage_name(bracket_size: int) -> str:
    return {2: "决赛", 4: "半决赛", 8: "八强", 16: "十六强", 32: "三十二强"}.get(
        bracket_size, f"Top {bracket_size}"
    )
