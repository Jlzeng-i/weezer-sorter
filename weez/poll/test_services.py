from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
import uuid
from .models import Album, Song, Vote, Voter
from .services import (
    get_or_create_voter,
    get_ranking,
    get_voter,
    record_vote,
    get_pool,
    next_matchup,
)
 
 
def make_request():
    """A fake request with a working session."""
    request = RequestFactory().get("/")
    SessionMiddleware(lambda r: None).process_request(request)
    return request
 
 
class ServicesTestCase(TestCase):
    """Shared setup: one album with songs A, B, C and one voter."""
 
    def setUp(self):
        self.album = Album.objects.create(title="Test Album")
        self.album2 = Album.objects.create(title="Test Album2")
        self.a = Song.objects.create(album=self.album, title="A")
        self.b = Song.objects.create(album=self.album, title="B")
        self.c = Song.objects.create(album=self.album, title="C")
        self.d = Song.objects.create(album=self.album2, title="D")
        self.voter = Voter.objects.create()
 
 
class VoterTests(ServicesTestCase):
    def test_no_voter_in_fresh_session(self):
        self.assertIsNone(get_voter(make_request()))
 
    def test_get_or_create_voter_reuses_the_same_voter(self):
        request = make_request()
        first = get_or_create_voter(request)
        second = get_or_create_voter(request)
        self.assertEqual(first, second)
        # setUp made one voter, the helper made one more, and not a third.
        self.assertEqual(Voter.objects.count(), 2)
    
    def test_get_voter_returns_none_for_invalid_uuid(self):
        request = make_request()
        request.session["voter_id"] = "invalid-uuid"
        self.assertIsNone(get_voter(request))
    
    def test_get_voter_returns_none_for_nonexistent_voter(self):
        request = make_request()
        request.session["voter_id"] = str(uuid.uuid4())  # random UUID not in DB
        self.assertIsNone(get_voter(request))
 
 
class RecordVoteTests(ServicesTestCase):
    def test_vote_is_saved(self):
        vote = record_vote(self.voter, self.a.id, self.b.id)
        self.assertEqual(Vote.objects.count(), 1)
        self.assertEqual(vote.winner, self.a)
        self.assertEqual(vote.loser, self.b)
 
    def test_implied_vote_is_ignored(self):
        record_vote(self.voter, self.a.id, self.b.id)   # A beats B
        record_vote(self.voter, self.b.id, self.c.id)   # B beats C
        # A beats C is now implied, so this should be skipped, not saved.
        self.assertIsNone(record_vote(self.voter, self.a.id, self.c.id))
        self.assertEqual(Vote.objects.count(), 2)

    def test_vote_against_itself_raises(self):
        with self.assertRaises(ValueError):
            record_vote(self.voter, self.a.id, self.a.id)
    
    def test_vote_with_nonexistent_song_raises(self):
        with self.assertRaises(ValueError):
            record_vote(self.voter, self.a.id, 9999)  # 9999 does not exist
    
    def test_vote_with_contradictory_order_is_ignored(self):
        record_vote(self.voter, self.a.id, self.b.id)  # A beats B
        # Now try to record B beats A, which contradicts the previous vote.
        self.assertIsNone(record_vote(self.voter, self.b.id, self.a.id))
        self.assertEqual(Vote.objects.count(), 1)
    
    def test_vote_with_string_ids_is_handled(self):
        vote = record_vote(self.voter, str(self.a.id), str(self.b.id))
        self.assertEqual(Vote.objects.count(), 1)
        self.assertEqual(vote.winner, self.a)
        self.assertEqual(vote.loser, self.b)
 
 
class RankingTests(ServicesTestCase):
    def test_ranking_follows_votes(self):
        record_vote(self.voter, self.a.id, self.b.id)
        record_vote(self.voter, self.b.id, self.c.id)
        songs, prog = get_ranking(self.voter, [self.album.id])
        self.assertEqual(songs, [self.a, self.b, self.c])
        self.assertEqual(prog, 1.0)

class PoolTests(ServicesTestCase):
    def test_get_pool_empty_when_no_album_ids(self):
        self.assertEqual(get_pool(), [])
    def test_get_pool_returns_songs_for_album_ids(self):
        self.assertEqual(set(get_pool([self.album.id])), {self.a.id, self.b.id, self.c.id})
        self.assertEqual(set(get_pool([self.album.id, self.album2.id])), {self.a.id, self.b.id, self.c.id, self.d.id})
    def test_next_matchup_returns_none_when_no_pairs_left(self):
        record_vote(self.voter, self.a.id, self.b.id)
        record_vote(self.voter, self.b.id, self.c.id)
        self.assertIsNone(next_matchup(self.voter, [self.album.id]))
    def test_next_matchup_returns_pair_when_available(self):
        pair = next_matchup(self.voter, [self.album.id])
        self.assertIsNotNone(pair)
        self.assertNotEqual(pair[0], pair[1])
        self.assertIn(pair[0], [self.a, self.b, self.c])
        self.assertIn(pair[1], [self.a, self.b, self.c])