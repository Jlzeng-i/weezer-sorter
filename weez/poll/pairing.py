"""
Pair selection that uses transitivity to skip questions the voter has already
answered indirectly.
"""
import random
from collections import defaultdict

_EMPTY = frozenset()


def known_order(edges):
    """
    Work out everything a voter's direct votes imply.

    Returns (down, up):
      down[s] = songs known to rank below s (directly or through a chain)
      up[s]   = songs known to rank above s
    Songs with nothing known in a given direction are absent from that dict.
    """
    beats = defaultdict(set)
    for winner, loser in edges:
        beats[winner].add(loser)

    down = {}
    for start in beats:
        seen = set()
        stack = list(beats[start])
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(beats.get(node, ()))
        seen.discard(start)  # inconsistent votes can loop back to the start
        down[start] = seen

    up = defaultdict(set)
    for winner, losers in down.items():
        for loser in losers:
            up[loser].add(winner)
    return down, dict(up)


def pick_pair(pool, edges, rng=random):
    """
    Choose the next two songs to show, or None if nothing is left to ask.

    pool:  song IDs eligible right now (e.g. the albums the user ticked).
           Votes involving songs outside the pool still count as evidence.
    edges: this voter's (winner_id, loser_id) votes.
    """
    pool = list(dict.fromkeys(pool))
    down, up = known_order(edges)

    best_score = 0
    best_pairs = []
    for i, a in enumerate(pool):
        for b in pool[i + 1:]:
            if b in down.get(a, _EMPTY) or a in down.get(b, _EMPTY):
                continue  # order already known or implied: never ask

            # If a wins, everything at-or-above a now beats everything
            # at-or-below b. Score a pair by its WORST outcome, so we favor
            # questions that teach us a lot whichever way the voter answers.
            gain_if_a = (len(up.get(a, _EMPTY)) + 1) * (len(down.get(b, _EMPTY)) + 1)
            gain_if_b = (len(up.get(b, _EMPTY)) + 1) * (len(down.get(a, _EMPTY)) + 1)
            score = min(gain_if_a, gain_if_b)

            if score > best_score:
                best_score, best_pairs = score, [(a, b)]
            elif score == best_score:
                best_pairs.append((a, b))

    if not best_pairs:
        return None
    pair = list(rng.choice(best_pairs))
    rng.shuffle(pair)  # don't always put the same song on the left
    return tuple(pair)


def rank_songs(pool, edges):
    """
    Order songs best-first using everything known or implied.

    Score = songs known to be worse minus songs known to be better. For a
    fully resolved order this is exact; songs not yet separated keep pool order.
    """
    down, up = known_order(edges)

    def score(song):
        return len(down.get(song, _EMPTY)) - len(up.get(song, _EMPTY))

    return sorted(pool, key=score, reverse=True)


def progress(pool, edges):
    """Fraction (0 to 1) of song pairs in the pool whose order is known."""
    pool = list(dict.fromkeys(pool))
    total = len(pool) * (len(pool) - 1) // 2
    if total == 0:
        return 1.0
    down, _ = known_order(edges)
    resolved = sum(
        1
        for i, a in enumerate(pool)
        for b in pool[i + 1:]
        if b in down.get(a, _EMPTY) or a in down.get(b, _EMPTY)
    )
    return resolved / total
