import json
from pathlib import Path
 
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
 
from poll.models import Album, Song
 
DEFAULT_FILE = Path(__file__).resolve().parents[2] / "data" / "discography.json"
 
 
class Command(BaseCommand):
    help = "Load albums and songs from a JSON file. Safe to run repeatedly."
 
    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=Path,
            default=DEFAULT_FILE,
            help=f"Path to the discography JSON (default: {DEFAULT_FILE})",
        )
 
    @transaction.atomic
    def handle(self, *args, **options):
        path = options["file"]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise CommandError(f"File not found: {path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in {path}: {e}")
 
        albums_created = songs_created = 0
 
        for entry in data["albums"]:
            album, created = Album.objects.get_or_create(title=entry["title"])
            albums_created += created
 
            # Keep ordering in sync with the file, but never touch cover_image.
            if album.sort_order != entry.get("sort_order", 0):
                album.sort_order = entry.get("sort_order", 0)
                album.save(update_fields=["sort_order"])
 
            for title in entry["songs"]:
                # get_or_create keyed on (album, title) means reruns won't create
                # duplicates or overwrite spotify_id/youtube_id filled in later.
                _, created = Song.objects.get_or_create(album=album, title=title)
                songs_created += created
 
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {albums_created} albums and {songs_created} songs "
                f"({Album.objects.count()} albums, {Song.objects.count()} songs total)."
            )
        )
