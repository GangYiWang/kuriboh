from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from random import Random
from uuid import UUID


@dataclass(frozen=True)
class StandingInput:
    participant_id: UUID
    nickname: str
    wins: int = 0
    losses: int = 0
    rank: int = 0
    bye_count: int = 0


@dataclass(frozen=True)
class Pairing:
    player_a_id: UUID
    player_b_id: UUID | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class MatchRecord:
    round_no: int
    player_a_id: UUID
    player_b_id: UUID | None
    winner_id: UUID


@dataclass(frozen=True)
class Ranking:
    participant_id: UUID
    nickname: str
    rank: int
    wins: int
    losses: int
    omw: float
    loss_round_score: int


def choose_bye_player(players: list[StandingInput], rng: Random) -> StandingInput:
    """Prefer no prior BYE, then the lowest score group and lowest current rank."""
    if not players:
        raise ValueError("cannot choose a BYE from an empty field")
    tie_breaks = {player.participant_id: rng.random() for player in players}
    return min(
        players,
        key=lambda player: (
            player.bye_count > 0,
            player.wins,
            -player.rank,
            tie_breaks[player.participant_id],
        ),
    )


def generate_swiss_pairings(
    players: list[StandingInput],
    prior_pairs: set[frozenset[UUID]],
    rng: Random,
) -> list[Pairing]:
    if len({player.participant_id for player in players}) != len(players):
        raise ValueError("participants must be unique")
    if not players:
        return []

    field = list(players)
    bye: StandingInput | None = None
    if len(field) % 2:
        bye = choose_bye_player(field, rng)
        field.remove(bye)

    random_noise: dict[frozenset[UUID], int] = {}
    for index, left in enumerate(field):
        for right in field[index + 1 :]:
            random_noise[frozenset((left.participant_id, right.participant_id))] = rng.randrange(100)

    def pair_cost(left: StandingInput, right: StandingInput) -> int:
        pair = frozenset((left.participant_id, right.participant_id))
        repeat_cost = 1_000_000 if pair in prior_pairs else 0
        score_gap_cost = abs(left.wins - right.wins) * 10_000
        return repeat_cost + score_gap_cost + random_noise[pair]

    if len(field) <= 18:
        @lru_cache(maxsize=None)
        def solve(remaining: tuple[int, ...]) -> tuple[int, tuple[tuple[int, int], ...]]:
            if not remaining:
                return 0, ()
            first = remaining[0]
            best: tuple[int, tuple[tuple[int, int], ...]] | None = None
            for position in range(1, len(remaining)):
                second = remaining[position]
                tail = remaining[1:position] + remaining[position + 1 :]
                tail_cost, tail_pairs = solve(tail)
                candidate = (pair_cost(field[first], field[second]) + tail_cost, ((first, second),) + tail_pairs)
                if best is None or candidate[0] < best[0]:
                    best = candidate
            assert best is not None
            return best

        _, index_pairs = solve(tuple(range(len(field))))
        matched = [(field[left], field[right]) for left, right in index_pairs]
    else:
        remaining_players = sorted(field, key=lambda player: (-player.wins, player.rank, player.nickname.casefold()))
        matched: list[tuple[StandingInput, StandingInput]] = []
        while remaining_players:
            left = remaining_players.pop(0)
            best_index = min(
                range(len(remaining_players)),
                key=lambda index: pair_cost(left, remaining_players[index]),
            )
            matched.append((left, remaining_players.pop(best_index)))

    pairings: list[Pairing] = []
    for left, right in matched:
        warnings: list[str] = []
        if frozenset((left.participant_id, right.participant_id)) in prior_pairs:
            warnings.append("重复对手")
        if left.wins != right.wins:
            warnings.append("跨胜场组")
        pairings.append(Pairing(left.participant_id, right.participant_id, tuple(warnings)))
    if bye:
        warnings = ("重复 BYE",) if bye.bye_count else ()
        pairings.append(Pairing(bye.participant_id, None, warnings))
    return pairings


def validate_pairing_draft(pairings: list[Pairing], active_ids: set[UUID]) -> list[str]:
    seen: list[UUID] = []
    errors: list[str] = []
    for pairing in pairings:
        seen.append(pairing.player_a_id)
        if pairing.player_b_id is not None:
            if pairing.player_a_id == pairing.player_b_id:
                errors.append("存在选手与自己配对")
            seen.append(pairing.player_b_id)
    if len(seen) != len(set(seen)):
        errors.append("同一选手在本轮重复出现")
    if set(seen) != active_ids:
        errors.append("本轮对阵未完整覆盖所有有效选手")
    bye_count = sum(pairing.player_b_id is None for pairing in pairings)
    if bye_count != len(active_ids) % 2:
        errors.append("BYE 数量与有效参赛人数不一致")
    return errors


def calculate_rankings(
    players: list[StandingInput],
    matches: list[MatchRecord],
) -> list[Ranking]:
    player_by_id = {player.participant_id: player for player in players}
    wins = {player.participant_id: 0 for player in players}
    losses = {player.participant_id: 0 for player in players}
    completed = {player.participant_id: 0 for player in players}
    opponents: dict[UUID, list[UUID]] = {player.participant_id: [] for player in players}
    loss_score = {player.participant_id: 0 for player in players}
    head_to_head: dict[tuple[UUID, UUID], UUID] = {}

    for match in matches:
        wins[match.winner_id] += 1
        completed[match.player_a_id] += 1
        if match.player_b_id is None:
            continue
        completed[match.player_b_id] += 1
        loser_id = match.player_b_id if match.winner_id == match.player_a_id else match.player_a_id
        losses[loser_id] += 1
        loss_score[loser_id] += match.round_no**2
        opponents[match.player_a_id].append(match.player_b_id)
        opponents[match.player_b_id].append(match.player_a_id)
        head_to_head[(match.player_a_id, match.player_b_id)] = match.winner_id
        head_to_head[(match.player_b_id, match.player_a_id)] = match.winner_id

    omw: dict[UUID, float] = {}
    for player_id, opponent_ids in opponents.items():
        rates = [wins[opponent_id] / completed[opponent_id] for opponent_id in opponent_ids if completed[opponent_id]]
        omw[player_id] = sum(rates) / len(rates) if rates else 0.0

    base_groups: dict[tuple[int, float, int], list[UUID]] = {}
    for player in players:
        key = (wins[player.participant_id], round(omw[player.participant_id], 8), loss_score[player.participant_id])
        base_groups.setdefault(key, []).append(player.participant_id)

    direct_wins: dict[UUID, int] = {player.participant_id: 0 for player in players}
    for group_ids in base_groups.values():
        group = set(group_ids)
        for left in group_ids:
            for right in group:
                if left != right and head_to_head.get((left, right)) == left:
                    direct_wins[left] += 1

    ordered = sorted(
        players,
        key=lambda player: (
            -wins[player.participant_id],
            -omw[player.participant_id],
            -loss_score[player.participant_id],
            -direct_wins[player.participant_id],
            player.nickname.casefold(),
            str(player.participant_id),
        ),
    )
    return [
        Ranking(
            participant_id=player.participant_id,
            nickname=player.nickname,
            rank=index,
            wins=wins[player.participant_id],
            losses=losses[player.participant_id],
            omw=omw[player.participant_id],
            loss_round_score=loss_score[player.participant_id],
        )
        for index, player in enumerate(ordered, start=1)
    ]
