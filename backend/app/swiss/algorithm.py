from __future__ import annotations

from dataclasses import dataclass
from random import Random
from uuid import UUID

import networkx as nx


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


class PairingUnavailableError(RuntimeError):
    """Raised when the active field has no complete non-repeating pairing."""


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

    pair_count = len(field) // 2
    max_noise_total = pair_count * 99
    float_rank_weight = max_noise_total + 1
    group_rank_bounds: dict[int, tuple[int, int]] = {}
    for player in field:
        minimum, maximum = group_rank_bounds.get(player.wins, (player.rank, player.rank))
        group_rank_bounds[player.wins] = (min(minimum, player.rank), max(maximum, player.rank))
    max_float_rank_penalty = max(
        (maximum - minimum for minimum, maximum in group_rank_bounds.values()),
        default=0,
    )
    cross_group_weight = pair_count * max_float_rank_penalty * float_rank_weight + max_noise_total + 1

    def pair_cost(left: StandingInput, right: StandingInput) -> int:
        pair = frozenset((left.participant_id, right.participant_id))
        score_gap = abs(left.wins - right.wins)
        if not score_gap:
            return random_noise[pair]
        higher_score_player = left if left.wins > right.wins else right
        lowest_group_rank = group_rank_bounds[higher_score_player.wins][1]
        float_rank_penalty = lowest_group_rank - higher_score_player.rank
        return cross_group_weight + float_rank_penalty * float_rank_weight + random_noise[pair]

    graph = nx.Graph()
    graph.add_nodes_from(range(len(field)))
    for left_index, left in enumerate(field):
        for right_index in range(left_index + 1, len(field)):
            right = field[right_index]
            pair = frozenset((left.participant_id, right.participant_id))
            if pair in prior_pairs or abs(left.wins - right.wins) > 1:
                continue
            graph.add_edge(left_index, right_index, weight=pair_cost(left, right))

    matching = nx.algorithms.matching.min_weight_matching(graph, weight="weight")
    if len(matching) != pair_count:
        raise PairingUnavailableError("没有可覆盖全部选手的无重复、相邻胜场组对阵方案")

    matched: list[tuple[StandingInput, StandingInput]] = []
    for first_index, second_index in matching:
        left, right = field[first_index], field[second_index]
        if (-right.wins, right.rank, right.nickname.casefold()) < (-left.wins, left.rank, left.nickname.casefold()):
            left, right = right, left
        matched.append((left, right))
    matched.sort(
        key=lambda pair: (
            -max(pair[0].wins, pair[1].wins),
            -min(pair[0].wins, pair[1].wins),
            min(pair[0].rank, pair[1].rank),
            pair[0].nickname.casefold(),
            pair[1].nickname.casefold(),
        )
    )

    pairings: list[Pairing] = []
    for left, right in matched:
        warnings: list[str] = []
        if left.wins != right.wins:
            warnings.append("跨胜场组")
        pairings.append(Pairing(left.participant_id, right.participant_id, tuple(warnings)))
    if bye:
        warnings = ("重复 BYE",) if bye.bye_count else ()
        pairings.append(Pairing(bye.participant_id, None, warnings))
    return pairings


def validate_pairing_draft(
    pairings: list[Pairing],
    active_ids: set[UUID],
    prior_pairs: set[frozenset[UUID]] | None = None,
    wins_by_id: dict[UUID, int] | None = None,
) -> list[str]:
    seen: list[UUID] = []
    errors: list[str] = []
    for pairing in pairings:
        seen.append(pairing.player_a_id)
        if pairing.player_b_id is not None:
            if pairing.player_a_id == pairing.player_b_id:
                errors.append("存在选手与自己配对")
            elif prior_pairs is not None and frozenset((pairing.player_a_id, pairing.player_b_id)) in prior_pairs:
                errors.append("存在重复对手")
            if wins_by_id is not None:
                player_a_wins = wins_by_id.get(pairing.player_a_id)
                player_b_wins = wins_by_id.get(pairing.player_b_id)
                if (
                    player_a_wins is not None
                    and player_b_wins is not None
                    and abs(player_a_wins - player_b_wins) > 1
                ):
                    errors.append("存在跨越非相邻胜场组的对阵")
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
