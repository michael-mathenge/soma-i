import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from rest_framework.decorators import api_view
from rest_framework.response import Response

from learners.accounts import email_value
from learners.email_delivery import available, deliver_preview
from learners.models import Account, AccountToken

GENERIC_REQUEST = {
    "detail": "If eligible, an in-memory preview message has been created. No email was sent."
}
INVALID_TOKEN = {"detail": "This link is invalid or expired. Request a new link."}


def state_digest(account):
    return salted_hmac(
        "somai-account-state-v1",
        f"{account.pk}:{account.email}:{account.user.password}:{account.email_verified_at}",
        algorithm="sha256",
    ).hexdigest()


def issue(account, purpose):
    raw = secrets.token_hex(32)
    now = timezone.now()
    AccountToken.objects.filter(
        account=account, purpose=purpose, used_at__isnull=True
    ).update(used_at=now)
    AccountToken.objects.create(
        account=account,
        digest=hashlib.sha256(raw.encode()).hexdigest(),
        purpose=purpose,
        state_digest=state_digest(account),
        expires_at=now + timedelta(seconds=86400 if purpose == "verify" else 1800),
    )
    deliver_preview(account.email, purpose, raw)


@api_view(["GET"])
def options(request):
    return Response(
        {
            "available": available(),
            "mode": "memory" if available() else "disabled",
            "live_delivery": False,
        }
    )


@api_view(["POST"])
def request_link(request, purpose):
    if not available():
        return Response(
            {"detail": "Account email delivery is unavailable."}, status=503
        )
    if not isinstance(request.data, dict) or purpose not in {"verify", "reset"}:
        return Response({"detail": "Invalid request."}, status=400)
    if purpose == "verify" and not request.user.is_authenticated:
        return Response({"detail": "Sign in first."}, status=401)
    if purpose == "reset" and request.user.is_authenticated:
        return Response(
            {"detail": "Sign out before requesting password recovery."}, status=409
        )
    try:
        create_preview(request, purpose)
    except RuntimeError:
        return Response({"detail": "Account preview is unavailable."}, status=503)
    return Response(GENERIC_REQUEST, status=202)


@transaction.atomic
def create_preview(request, purpose):
    with transaction.atomic():
        accounts = (
            Account.objects.select_for_update()
            .select_related("user")
            .filter(user__is_active=True)
        )
        if purpose == "verify":
            account = accounts.filter(
                user=request.user, email_verified_at__isnull=True
            ).first()
        else:
            try:
                email = email_value(request.data)
            except ValidationError:
                email = ""
            account = accounts.filter(
                email=email, email_verified_at__isnull=False
            ).first()
        if account:
            issue(account, purpose)


@api_view(["POST"])
def confirm(request, purpose):
    if not available():
        return Response(
            {"detail": "Account email delivery is unavailable."}, status=503
        )
    if not isinstance(request.data, dict):
        return Response(INVALID_TOKEN, status=400)
    raw = request.data.get("token")
    if (
        not isinstance(raw, str)
        or len(raw) != 64
        or any(char not in "0123456789abcdef" for char in raw)
    ):
        return Response(INVALID_TOKEN, status=400)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    # Always acquire the account before its token, matching request_link's lock order.
    account_id = (
        AccountToken.objects.filter(digest=digest, purpose=purpose)
        .values_list("account_id", flat=True)
        .first()
    )
    with transaction.atomic():
        account = (
            Account.objects.select_for_update()
            .select_related("user")
            .filter(pk=account_id, user__is_active=True)
            .first()
        )
        token = (
            AccountToken.objects.select_for_update()
            .filter(digest=digest, purpose=purpose)
            .first()
        )
        if (
            not account
            or not token
            or token.used_at
            or token.expires_at <= timezone.now()
            or not constant_time_compare(token.state_digest, state_digest(account))
        ):
            return Response(INVALID_TOKEN, status=400)
        if request.user.is_authenticated and request.user.pk != account.user_id:
            return Response(INVALID_TOKEN, status=400)
        if purpose == "verify":
            if account.email_verified_at:
                return Response(INVALID_TOKEN, status=400)
            account.email_verified_at = timezone.now()
            account.save(update_fields=["email_verified_at"])
        elif purpose == "reset":
            if not account.email_verified_at:
                return Response(INVALID_TOKEN, status=400)
            password = request.data.get("password")
            try:
                if not isinstance(password, str) or not 12 <= len(password) <= 128:
                    raise ValidationError("Use a password of 12-128 characters.")
                validate_password(password, account.user)
            except ValidationError as error:
                return Response({"detail": " ".join(error.messages)}, status=400)
            account.user.set_password(password)
            account.user.save(update_fields=["password"])
        else:
            return Response(INVALID_TOKEN, status=400)
        AccountToken.objects.filter(account=account, used_at__isnull=True).update(
            used_at=timezone.now()
        )
    if purpose == "reset":
        # Password auth-hash changes invalidate the account's other Django sessions.
        logout(request)
    return Response({"confirmed": True, "csrf_token": get_token(request)})
