from django.contrib import admin
from django.db.models import Count

from .models import Album, Song, Vote, Voter


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("title", "sort_order", "song_count")
    list_editable = ("sort_order",)  # reorder albums right from the list page
    search_fields = ("title",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_song_count=Count("songs"))

    @admin.display(description="Songs", ordering="_song_count")
    def song_count(self, obj):
        return obj._song_count


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ("title", "album", "spotify_id", "youtube_id")
    list_filter = ("album",)
    search_fields = ("title",)
    list_select_related = ("album",)  # avoids one extra query per row
    list_editable = ("spotify_id", "youtube_id")


@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "country", "region", "created_at")
    list_filter = ("country",)
    readonly_fields = ("id", "created_at")


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    # Votes come from the app, not from hand entry, so treat them as read-only.
    list_display = ("winner", "loser", "voter", "created_at")
    list_select_related = ("winner", "loser", "voter")
    date_hierarchy = "created_at"
    readonly_fields = ("voter", "winner", "loser", "created_at")

    def has_add_permission(self, request):
        return False