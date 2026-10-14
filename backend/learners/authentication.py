from rest_framework.authentication import SessionAuthentication


class GuestSessionAuthentication(SessionAuthentication):
    """Require CSRF on unsafe requests even before a user has logged in."""

    def authenticate(self, request):
        self.enforce_csrf(request)
        return super().authenticate(request)


class PrivateAPIHeaders:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/") and request.path not in {
            "/api/health/",
            "/api/pathways/",
        }:
            response["Cache-Control"] = "private, no-store"
        return response
