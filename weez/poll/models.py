import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Album(models.Model):
    title = models.CharField(max_length=200, unique=True)
    # Optional: albums like "Unreleased / Demos" can simply have no cover.
    cover_image = models.ImageField(upload_to="album_covers/", blank=True)
    # Controls display order (checkbox list, etc.). Lower comes first;
    # give the miscellaneous album a high number to sit at the end.
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self):
        return self.title


class Song(models.Model):
    title = models.CharField(max_length=200)
    album = models.ForeignKey(
        Album,
        on_delete=models.PROTECT,  # can't delete an album that still has songs
        related_name="songs",
    )
    # Filled in later for embeds; blank is fine until then.
    spotify_id = models.CharField(max_length=40, blank=True)
    youtube_id = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["album__sort_order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["album", "title"], name="unique_song_per_album"
            ),
        ]

    def __str__(self):
        return self.title


class Voter(models.Model):
    """
    One row per person ranking songs. Starts anonymous (the id lives in the
    session); later `user` is linked when they create an account.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="voter",
    )
    # Coarse location only, as ISO codes. Never store IP addresses.
    country = models.CharField(max_length=2, blank=True)  # ISO 3166-1, e.g. "US"
    region = models.CharField(max_length=6, blank=True)  # ISO 3166-2 part, e.g. "MA"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class Vote(models.Model):
    """One matchup result. Rankings and stats are computed from these rows."""

    voter = models.ForeignKey(Voter, on_delete=models.CASCADE, related_name="votes")
    winner = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="wins")
    loser = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="losses")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Django 5.1+ uses `condition=`; on older versions use `check=`.
            models.CheckConstraint(
                condition=~Q(winner=F("loser")), name="winner_not_loser"
            ),
        ]
        indexes = [
            models.Index(fields=["voter", "created_at"]),
        ]

    def __str__(self):
        return f"{self.winner} beat {self.loser}"
