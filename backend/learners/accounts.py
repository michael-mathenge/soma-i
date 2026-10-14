from uuid import uuid4

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from rest_framework.decorators import api_view
from rest_framework.response import Response

from learners.models import Account, LearnerProfile


def email_value(data):
    value = data.get("email")
    if not isinstance(value, str) or len(value) > 254:
        raise ValidationError("Enter a valid email address.")
    value = value.strip().lower()
    validate_email(value)
    return value


@api_view(["GET"])
def csrf(request):
    return Response({"csrf_token": get_token(request)})


@api_view(["GET", "POST", "DELETE"])
def account(request):
    if request.method != "GET" and not isinstance(request.data, dict):
        return Response({"detail": "Use a JSON object."}, status=400)
    if request.method == "GET":
        if not request.user.is_authenticated:
            return Response({"authenticated": False})
        identity = Account.objects.filter(user=request.user).first()
        return Response(
            {
                "authenticated": True,
                "email": identity.email if identity else "",
                "email_verified": False,
            }
        )
    if request.method == "DELETE":
        if not request.user.is_authenticated:
            return Response({"detail": "Sign in first."}, status=401)
        password = request.data.get("password")
        if (
            not isinstance(password, str)
            or len(password) > 1024
            or not request.user.check_password(password)
        ):
            return Response({"detail": "Password confirmation failed."}, status=400)
        with transaction.atomic():
            request.user.delete()
            logout(request)
        return Response({"deleted": True, "csrf_token": get_token(request)})
    if request.user.is_authenticated:
        return Response({"detail": "Sign out before creating an account."}, status=409)
    try:
        email = email_value(request.data)
        password = request.data.get("password")
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            raise ValidationError("Use a password of 12-128 characters.")
        candidate = get_user_model()(username=uuid4().hex, email=email)
        validate_password(password, candidate)
        attach = request.data.get("attach_guest", False)
        if type(attach) is not bool:
            raise ValidationError("Choose whether to attach this guest's progress.")
        with transaction.atomic():
            guest = None
            if attach:
                if request.session.get("demo_session"):
                    raise ValidationError("Shared demo progress cannot be attached.")
                guest = (
                    LearnerProfile.objects.select_for_update()
                    .filter(pk=request.session.get("learner_id"), owner__isnull=True)
                    .first()
                )
                if guest is None:
                    raise ValidationError("No current guest profile to attach.")
            candidate.set_password(password)
            candidate.save()
            Account.objects.create(user=candidate, email=email)
            if guest:
                guest.owner = candidate
                guest.save(update_fields=["owner"])
    except ValidationError as error:
        return Response({"detail": " ".join(error.messages)}, status=400)
    except IntegrityError:
        return Response(
            {"detail": "Account could not be created with these details."}, status=400
        )
    request.session.pop("learner_id", None)
    request.session.pop("demo_session", None)
    login(request, candidate, backend="django.contrib.auth.backends.ModelBackend")
    return Response(
        {"authenticated": True, "csrf_token": get_token(request)}, status=201
    )


@api_view(["POST"])
def sign_in(request):
    if not isinstance(request.data, dict):
        return Response({"detail": "Use a JSON object."}, status=400)
    if request.user.is_authenticated:
        return Response({"detail": "Sign out before switching accounts."}, status=409)
    try:
        email = email_value(request.data)
    except ValidationError:
        email = ""
    password = request.data.get("password")
    if not isinstance(password, str) or len(password) > 128:
        password = ""
    identity = Account.objects.select_related("user").filter(email=email).first()
    user = authenticate(
        request,
        username=identity.user.username if identity else "missing-account",
        password=password,
    )
    if user is None or identity is None or user.pk != identity.user_id:
        return Response({"detail": "Email or password is incorrect."}, status=400)
    # A different guest stays preserved, never silently attached on login.
    request.session.pop("learner_id", None)
    request.session.pop("demo_session", None)
    login(request, user)
    return Response({"authenticated": True, "csrf_token": get_token(request)})


@api_view(["POST"])
def sign_out(request):
    logout(request)
    return Response({"authenticated": False, "csrf_token": get_token(request)})
