from django.urls import path
from . import views

app_name = "poll"

urlpatterns = [
    path("", views.matchup, name="matchup"),
    path("ranking", views.ranking, name="ranking"),
]

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)