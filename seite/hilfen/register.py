"""Die eine Bibliothek ``seite`` für die Vorlagen (``{% load seite %}``)."""

from __future__ import annotations

from django import template

register = template.Library()
