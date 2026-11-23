"""Sicherheitskopfzeilen für alle Antworten."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from django.conf import settings

from .site import PREVIEW_COOKIE


def _origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}" if p.scheme and p.netloc else ""


# Origin aus HUBIplan oder der Einstellung: nur Schema, Hostname und Port, nichts, was die
# Kopfzeile verändern könnte
ORIGIN = re.compile(r"^https?://[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?(?::[0-9]{1,5})?$")


def clean_origin(value) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip().rstrip("/").lower()
    return value if ORIGIN.match(value) else ""


class SecurityHeaders:
    def __init__(self, get_response):
        self.get_response = get_response
        hubiplan = _origin(settings.HUBIPLAN_PUBLIC_URL)
        connect = " ".join(x for x in ("'self'", hubiplan) if x)
        form = " ".join(x for x in ("'self'", hubiplan) if x)
        policy = (
            "default-src 'self'; img-src 'self' data:; script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            f"connect-src {connect}; form-action {form}; frame-ancestors {{frames}}; "
            "base-uri 'self'; object-src 'none'"
        )
        self.policy = policy
        self.csp = policy.format(frames="'none'")
        # Vorschau im Rahmen neben den Einstellungen (Webseite › Gestaltung, Konzept G2):
        # einbetten darf nur HUBIplan selbst und nur bei Vorschau-Anfragen. Dazu kommen die
        # Vereinsadressen der Einheit, die HUBIplan mit der Vorschau meldet (Issue #729)
        self.frames = ["'self'", *(o for o in (hubiplan,) if o)]
        for extra in settings.HUBIPLAN_EXTRA_ORIGINS:
            origin = clean_origin(extra)
            if origin and origin not in self.frames:
                self.frames.append(origin)
        self.csp_preview = policy.format(frames=" ".join(self.frames))

    def preview_csp(self, request) -> str:
        frames = list(self.frames)
        for value in getattr(request, "vorschau_rahmen", None) or ():
            origin = clean_origin(value)
            if origin and origin not in frames:
                frames.append(origin)
        if len(frames) == len(self.frames):
            return self.csp_preview
        return self.policy.format(frames=" ".join(frames))

    def __call__(self, request):
        response = self.get_response(request)
        if _is_preview(request):
            response.setdefault("Content-Security-Policy", self.preview_csp(request))
            # X-Frame-Options: DENY nicht setzen (XFrameOptionsMiddleware läuft danach)
            response.xframe_options_exempt = True
        response.setdefault("Content-Security-Policy", self.csp)
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response


def _is_preview(request) -> bool:
    """Vorschau-Cookie gesetzt oder der Tausch des Vorschau-Schlüssels (…/vorschau/)."""
    return PREVIEW_COOKIE in request.COOKIES or request.path.rstrip("/").endswith("/vorschau")
