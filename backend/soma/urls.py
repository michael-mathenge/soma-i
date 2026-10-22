from django.urls import include, path, re_path

from soma.spa import ApplicationShell

# The API is mounted first so that /api/ paths are never handled by the
# single page application fallback. WhiteNoise serves the built assets and
# the application shell; this catch-all returns the shell for the remaining
# client-side routes.
urlpatterns = [
    path("api/", include("learners.urls")),
    re_path(r"^(?!api/).*$", ApplicationShell.as_view(), name="application-shell"),
]
