"""Sicherheitskopfzeilen für alle Antworten."""

from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings

from .site import PREVIEW_COOKIE


def _origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}" if p.scheme and p.netloc else ""


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
        self.csp = policy.format(frames="'none'")
        # Vorschau im Rahmen neben den Einstellungen (Webseite › Gestaltung, Konzept G2):
        # einbetten darf nur HUBIplan selbst und nur bei Vorschau-Anfragen
        frames = " ".join(x for x in ("'self'", hubiplan) if x)
        self.csp_preview = policy.format(frames=frames)

    def __call__(self, request):
        response = self.get_response(request)
        if _is_preview(request):
            response.setdefault("Content-Security-Policy", self.csp_preview)
            # X-Frame-Options: DENY nicht setzen (XFrameOptionsMiddleware läuft danach)
            response.xframe_options_exempt = True
        response.setdefault("Content-Security-Policy", self.csp)
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response


def _is_preview(request) -> bool:
    """Vorschau-Cookie gesetzt oder der Tausch des Vorschau-Schlüssels (…/vorschau/)."""
    return PREVIEW_COOKIE in request.COOKIES or request.path.rstrip("/").endswith("/vorschau")
