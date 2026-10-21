"""Serve the built single page application for client-side routes.

The frontend owns its routes, so a browser request for a path such as
/catalogue must return the application shell rather than a 404. The API
is mounted under /api/ and is never handled here.

The shell is read from the built bundle, which is also the directory the
static assets are served from.
"""

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponseNotFound
from django.urls import path
from django.views.generic import View


def bundle_directory():
    """Return the directory holding the built application bundle."""
    root = getattr(settings, "WHITENOISE_ROOT", None) or settings.STATIC_ROOT
    return Path(root)


class ApplicationShell(View):
    """Return the built index document for a client-side route."""

    def get(self, request, *args, **kwargs):
        index = bundle_directory() / "index.html"
        if not index.is_file():
            return HttpResponseNotFound("The application bundle is not built.")
        return FileResponse(index.open("rb"), content_type="text/html")


urlpatterns = [
    path("", ApplicationShell.as_view(), name="application-shell"),
]
