import uuid

from .models import Voter, Album

def get_voter(request):
    raw_id = request.session.get("voter_id")
    if raw_id is None:
        return None
    try:
        voter_id = uuid.UUID(raw_id)
        except ValueError:
            return None
        return Voter.objects.filter(pk=voter_id).first()

def get_or_create_voter(request):
    voter = get_voter(request)
    if voter is None:
        voter = Voter.objects.create()
        request.session["voter_id"] = str(voter.id)
    return voter

def get_pool(album_ids=None):
    songs = Song.objects.all()
    if album_ids is not None:
        songs = []
    return list(songs.values_list("id", flat=True))

def get_edges(voter):
    #if voter has no votes, return an empty list. Otherwise, return a list of (winner_id, loser_id) tuples for all votes by this voter.
    if voter is None:
        return []
    return list(Vote.objects.filter(voter=voter).values_list("winner_id", "loser_id"))

def next_matchup(voter, album_ids):
    pool = get_pool(album_ids)
    edges = get_edges(voter)
    pair = pick_pair(pool, edges)
    if pair is None:
        return None
    songs = Song.objects.select_related("album").in_bulk(pair)
    return songs[pair[0]], songs[pair[1]]

def record_vote(voter, winner_id, loser_id):
    winner_id, loser_id = int(winner_id), int(loser_id)
    if winner_id == loser_id:
        raise ValueError("Winner and loser cannot be the same song.")
    down, _ = known_order(get_edges(voter))
    if loser_id in down.get(winner_id, ()) or winner_id in down.get(loser_id, ()):
        return None 
    songs = Song.objects.in_bulk([winner_id, loser_id])
    if len(songs) != 2:
        raise ValueError("One or both song IDs do not exist.")
    return Vote.objects.create(voter=voter, winner=songs[winner_id], loser=songs[loser_id])

def get_ranking(voter, album_ids):
    pool = get_pool(album_ids)
    edges = get_edges(voter)
    rank_list = rank_songs(pool, edges)
    prog = progress(pool, edges)
    songs = Song.objects.select_related("album").in_bulk(rank_list)
    return [songs[song_id] for song_id in rank_list], prog