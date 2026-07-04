"""Google reCAPTCHA v2 checkbox and v3 score helpers."""

from __future__ import annotations

import json
import logging
import urllib.request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from django.conf import settings

logger = logging.getLogger(__name__)


def recaptcha_version() -> str:
    version = (getattr(settings, "RECAPTCHA_VERSION", "v2") or "v2").strip().lower()
    return version if version in {"v2", "v3"} else "v2"


def is_recaptcha_enabled() -> bool:
    if getattr(settings, "DEBUG", False) and getattr(settings, "RECAPTCHA_DISABLE_IN_DEBUG", True):
        if not getattr(settings, "RECAPTCHA_FORCE_IN_DEBUG", False):
            return False

    site_key = (getattr(settings, "RECAPTCHA_SITE_KEY", "") or "").strip()
    secret_key = (getattr(settings, "RECAPTCHA_SECRET_KEY", "") or "").strip()
    return bool(site_key and secret_key)


def recaptcha_template_context() -> dict[str, object]:
    return {
        "recaptcha_enabled": is_recaptcha_enabled(),
        "recaptcha_site_key": (getattr(settings, "RECAPTCHA_SITE_KEY", "") or "").strip(),
        "recaptcha_version": recaptcha_version(),
    }


def verify_recaptcha_token(token: str, remote_ip: str | None = None) -> tuple[bool, str | None]:
    if not is_recaptcha_enabled():
        return True, None

    if not token:
        return False, "Please complete the reCAPTCHA challenge."

    payload = urlencode(
        {
            "secret": (getattr(settings, "RECAPTCHA_SECRET_KEY", "") or "").strip(),
            "response": token,
            "remoteip": remote_ip or "",
        }
    ).encode("utf-8")
    request_obj = urllib.request.Request(
        "https://www.google.com/recaptcha/api/siteverify",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=10) as response:
            verification_result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        logger.warning("reCAPTCHA verification request failed.", exc_info=True)
        return False, "reCAPTCHA verification failed. Please try again."

    if not verification_result.get("success"):
        error_codes = verification_result.get("error-codes") or []
        if "invalid-input-secret" in error_codes or "invalid-keys" in error_codes:
            logger.error("reCAPTCHA secret key is invalid for version %s", recaptcha_version())
        return False, "reCAPTCHA verification failed. Please try again."

    if recaptcha_version() == "v3":
        try:
            score = float(verification_result.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        min_score = float(getattr(settings, "RECAPTCHA_V3_MIN_SCORE", 0.5))
        if score < min_score:
            return False, "reCAPTCHA verification failed. Please try again."

    return True, None
