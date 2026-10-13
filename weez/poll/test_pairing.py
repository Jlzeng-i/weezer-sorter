import random
import unittest

from .pairing import known_order, pick_pair, progress, rank_songs


class KnownOrderTests(unittest.TestCase):
    def test_chain_is_followed(self):
        down, up = known_order([(1, 2), (2, 3)])
        self.assertEqual(down[1], {2, 3})
        self.assertEqual(up[3], {1, 2})

    def test_inconsistent_votes_do_not_crash_or_loop(self):
        down, up = known_order([(1, 2), (2, 3), (3, 1)])
        self.assertNotIn(1, down[1])


class PickPairTests(unittest.TestCase):
    def test_pool_too_small(self):
        self.assertIsNone(pick_pair([1], []))
        self.assertIsNone(pick_pair([], []))

    def test_no_history_gives_two_distinct_pool_members(self):
        a, b = pick_pair([1, 2, 3, 4], [], random.Random(0))
        self.assertNotEqual(a, b)
        self.assertTrue({a, b} <= {1, 2, 3, 4})

    def test_implied_pair_is_never_asked(self):
        # 1>2 and 2>3 imply 1>3, so nothing is left to ask.
        self.assertIsNone(pick_pair([1, 2, 3], [(1, 2), (2, 3)]))

    def test_songs_outside_the_pool_still_imply(self):
        # 1>9>2 where 9 is not in the pool: 1 vs 2 is already settled.
        self.assertIsNone(pick_pair([1, 2], [(1, 9), (9, 2)]))

    def test_never_returns_a_resolved_pair(self):
        rng = random.Random(1)
        edges = [(1, 2), (3, 4)]
        for _ in range(50):
            a, b = pick_pair([1, 2, 3, 4], edges, rng)
            self.assertNotEqual({a, b}, {1, 2})
            self.assertNotEqual({a, b}, {3, 4})


class RankAndProgressTests(unittest.TestCase):
    def test_rank_follows_implied_order(self):
        self.assertEqual(rank_songs([3, 1, 2], [(1, 2), (2, 3)]), [1, 2, 3])

    def test_progress(self):
        self.assertEqual(progress([1, 2, 3], []), 0.0)
        self.assertAlmostEqual(progress([1, 2, 3], [(1, 2)]), 1 / 3)
        self.assertEqual(progress([1, 2, 3], [(1, 2), (2, 3)]), 1.0)


class SimulationTests(unittest.TestCase):
    def test_full_order_is_found_with_far_fewer_votes_than_pairs(self):
        rng = random.Random(42)
        pool = list(range(40))
        skill = {song: rng.random() for song in pool}  # the voter's hidden taste
        total_pairs = len(pool) * (len(pool) - 1) // 2

        edges = []
        while True:
            pair = pick_pair(pool, edges, rng)
            if pair is None:
                break
            a, b = pair
            winner, loser = (a, b) if skill[a] > skill[b] else (b, a)
            edges.append((winner, loser))
            self.assertLessEqual(len(edges), total_pairs)  # safety net

        self.assertEqual(
            rank_songs(pool, edges), sorted(pool, key=skill.get, reverse=True)
        )
        self.assertLess(len(edges), total_pairs / 2)
        self.assertEqual(progress(pool, edges), 1.0)
