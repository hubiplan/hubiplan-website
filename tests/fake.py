"""Eine erfundene HUBIplan-Schnittstelle für die Tests (alle Daten erfunden)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from seite import api

KEY = "testschluessel123"
BASE = f"https://hubiplan.example{api.PREFIX}{KEY}/"
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00"
    b"\x00\x00\x00IEND\xaeB`\x82"
)


def site_info(**over) -> dict:
    data = {
        "version": 1,
        "state": "public",
        "preview": False,
        "name": "Schützenverein Musterdorf 1900",
        "short_name": "SV Musterdorf",
        "logo_url": "https://hubiplan.example/media/logos/wappen.png",
        "theme": {
            "primary": "#123456",
            "on_primary": "#ffffff",
            "accent": "#abcdef",
            "on_accent": "#000000",
        },
        "imprint_url": BASE + "imprint/",
        "allow_indexing": True,
        "hubiplan_imprint": {},
        "founding_year": 1900,
        "unit_label": "Zug",
        "unit_label_plural": "Züge",
        "address": {"street": "Dorfstraße 1", "postal_code": "12345", "city": "Musterdorf"},
        "email": "info@musterdorf.example",
        "phone": None,
        "member_of": {"name": "Bürgerverein Musterdorf", "website": None},
        "blocks": {
            "events": True,
            "board": True,
            "honors": True,
            "history": True,
            "contact": True,
            "units": True,
            "social": True,
        },
        "menu": [
            {"slug": "geschichte", "title": "Geschichte"},
            {"slug": "anfahrt", "title": "Anfahrt"},
        ],
        "greeting": {
            "title": "Willkommen",
            "text": "Hallo **Welt**! <script>alert(1)</script>\n\n![Fest](bild:festbild1)",
            "image": None,
        },
        "social": [
            {
                "kind": "instagram",
                "label": "Instagram",
                "url": "https://instagram.example/sv",
                "display": "@sv",
            },
            {
                "kind": "facebook",
                "label": "Facebook",
                "url": "https://facebook.example/sv",
                "display": "",
            },
            {
                "kind": "tiktok",
                "label": "TikTok",
                "url": "https://tiktok.example/@sv",
                "display": "@sv",
            },
            {"kind": "x", "label": "X", "url": "https://x.example/sv", "display": "@sv"},
        ],
        "units": [
            {
                "slug": "jaeger",
                "name": "Jägerzug",
                "short_name": "",
                "founding_year": 1950,
                "parent": None,
                "logo_url": None,
                "image": None,
            },
        ],
        "statute_url": None,
        "fee_rules_url": None,
        "founding_deed_url": None,
        "calendar": {"json_url": BASE + "events/", "ics_url": BASE + "events.ics"},
    }
    data.update(over)
    return data


BOARD = {
    "roles": [
        {
            "id": "r1" * 10,
            "name": "1. Vorsitzender",
            "holders": [
                {
                    "name": "Max Muster",
                    "photo_url": BASE + "photos/" + "a" * 20 + "/",
                    "email": "max@musterdorf.example",
                }
            ],
            "vacant": False,
            "email": None,
            "contact_form": True,
        },
        {
            "id": "r2" * 10,
            "name": "Kassierer",
            "holders": [],
            "vacant": True,
            "email": None,
            "contact_form": False,
        },
    ],
    "honorary": [
        {
            "title": "Ehrenmitglied",
            "holders": [{"name": "Erika Beispiel", "photo_url": None, "since": "2010-05-01"}],
        }
    ],
    "chronicle": [
        {
            "role": "1. Vorsitzender",
            "holders": [
                {
                    "name": "Alt Vorsitz",
                    "photo_url": None,
                    "from": "2000-01-01",
                    "until": "2019-12-31",
                    "current": False,
                },
                {
                    "name": "Max Muster",
                    "photo_url": None,
                    "from": "2020-01-01",
                    "until": None,
                    "current": True,
                },
            ],
        },
    ],
}

HONORS = {
    "dignities": [
        {
            "id": "d" * 20,
            "name": "König",
            "name_plural": "Könige",
            "current": [
                {
                    "year": 2026,
                    "from": None,
                    "until": None,
                    "period": "2026",
                    "holder": {"name": "Karl Krone", "photo_url": None},
                    "companions": [{"label": "Königin", "name": "Klara Krone", "photo_url": None}],
                    "note": "",
                    "photo_url": None,
                    "times": 2,
                }
            ],
            "reigns": [
                {
                    "year": 2026,
                    "period": "2026",
                    "holder": {"name": "Karl Krone"},
                    "companions": [],
                    "note": "",
                    "photo_url": None,
                    "times": 2,
                },
                {
                    "year": 2025,
                    "period": "2025",
                    "holder": {"name": "Otto Ober"},
                    "companions": [],
                    "note": "",
                    "photo_url": None,
                    "times": 1,
                },
            ],
        }
    ]
}


COMP = "c" * 20
LIVE = "1" * 20
SERIES = "5" * 20


def _comp(token: str, title: str, *, live: bool = False) -> dict:
    return {
        "id": token,
        "title": title,
        "date": "2027-06-14",
        "year": 2027,
        "occasion": "",
        "discipline": "Luftgewehr",
        "location": "Schießstand",
        "own": True,
        "organizer": "",
        "status": "laeuft" if live else "endgueltig",
        "live": live,
        "provisional": False,
        "final": not live,
        "url": f"{BASE}results/{token}/",
    }


def results_detail(token: str, version: str = "v1") -> dict:
    live = token == LIVE
    return {
        **_comp(token, "Pokalschießen" if live else "Vereinsmeisterschaft 2027", live=live),
        "description": "",
        "details": "",
        "depth": "alle",
        "scorings": [
            {
                "name": "Einzel",
                "kind": "einzel",
                "field": 4,
                "complete": True,
                "rows": [
                    {"place": 1, "value": "30", "prize": False, "name": "Max M.", "unit": "Zug 1"},
                    {"place": 2, "value": "28", "prize": False, "name": "ohne Namen", "unit": ""},
                    {
                        "place": 3,
                        "value": "20",
                        "prize": False,
                        "name": "Gerd G.",
                        "unit": "",
                        "club": "Nachbarverein",
                    },
                ],
            }
        ],
        "prizes": [],
        "titles": [] if live else [{"title": "Vereinsmeister 2027", "name": "Max M."}],
        "version": version,
        "poll_seconds": 15 if live else None,
        "version_url": f"{BASE}results/{token}/version/",
    }


def results_overview() -> dict:
    return {
        "competitions": [
            _comp(LIVE, "Pokalschießen", live=True),
            _comp(COMP, "Vereinsmeisterschaft 2027"),
        ],
        "series": [
            {"id": SERIES, "name": "Vereinsmeisterschaft", "url": f"{BASE}results/series/{SERIES}/"}
        ],
        "trophies": [
            {
                "name": "Zugpokal",
                "description": "",
                "holders": [{"year": 2026, "name": "Zug 1", "kept": False}],
            }
        ],
        "poll_seconds": 15,
    }


def results_series() -> dict:
    return {
        "id": SERIES,
        "name": "Vereinsmeisterschaft",
        "description": "Jedes Jahr im Juni.",
        "years": [
            {
                "year": 2027,
                "title": "Vereinsmeisterschaft 2027",
                "url": f"{BASE}results/{COMP}/",
                "winners": [{"scoring": "Einzel", "names": ["Max M."], "value": "30"}],
                "depth": "alle",
            }
        ],
        "titles": [
            {"year": 2027, "title": "Vereinsmeister 2027", "name": "Max M."},
            {"year": 1999, "title": "Vereinsmeister 1999", "name": "Karl F."},
        ],
    }


def events(future: str = "2099-06-01T18:00:00+02:00") -> dict:
    return {
        "ics_url": BASE + "events.ics",
        "events": [
            {
                "id": "e1",
                "title": "Schützenfest",
                "starts_at": future,
                "ends_at": "2099-06-01T23:00:00+02:00",
                "all_day": False,
                "location": "Festzelt",
                "address": "",
                "description": "Mit Musik",
                "category": None,
                "color": None,
                "unit": None,
                "owner": "Bürgerverein Musterdorf",
                "is_cancelled": False,
                "note": "",
            },
            {
                "id": "e0",
                "title": "Alter Termin",
                "starts_at": "2000-01-01T10:00:00+01:00",
                "ends_at": None,
                "all_day": False,
                "location": "",
                "address": "",
                "description": "",
                "category": None,
                "color": None,
                "unit": None,
                "is_cancelled": False,
                "note": "",
            },
        ],
    }


def _post(n: int, kind: str, text: str, images: int = 1, video: bool = False) -> dict:
    return {
        "id": f"beitrag{n}",
        "kind": kind,
        "kind_label": "Instagram" if kind == "instagram" else "Facebook",
        "account": "musterdorf",
        "media_type": "video" if video else ("album" if images > 1 else "image"),
        "text": text,
        "published_at": f"2026-10-{20 - n:02d}T10:00:00+00:00",
        "permalink": f"https://www.instagram.com/p/beispiel{n}/" if kind == "instagram" else None,
        "images": [
            {
                "url": f"{BASE}posts/images/bild{n}x{i}/",
                "small_url": f"{BASE}posts/images/bild{n}x{i}/?size=small",
                "width": 1200,
                "height": 900,
                "alt": "Erfundenes Bild",
                "is_video": video,
            }
            for i in range(images)
        ],
    }


POSTS = [
    _post(1, "instagram", "Schönes Fest!\nDanke an alle <b>Helfer</b>.", images=3),
    _post(2, "instagram", "Probe für den Umzug.", video=True),
    _post(3, "facebook", "Einladung zur Versammlung.", images=0),
]


@dataclass
class FakeHubiplan:
    info: dict = field(default_factory=site_info)
    maintenance: bool = False
    preview_session: str = "sitzung-1234567890"
    calls: list = field(default_factory=list)
    posts: list = field(default_factory=list)
    bases: list = field(default_factory=list)
    hosts: dict = field(default_factory=lambda: {"testserver": KEY, "www.musterdorf.test": KEY})
    # Stand je Wettbewerb (Wettbewerbsergebnisse live)
    versions: dict = field(default_factory=dict)
    # Eingespielte Designpakete (Schlüssel → Antwort von design/<schlüssel>/)
    packages: dict = field(default_factory=dict)
    # Antworten weiterer Pfade (Tests), z. B. {"repertoire/": {...}}
    antworten: dict = field(default_factory=dict)

    def __call__(self, method, path, *, data=None, preview=None, base=None):
        self.calls.append((method, path, preview))
        self.bases.append(base)
        ok_preview = preview == self.preview_session
        prefix = f"{api.PREFIX}{KEY}/"
        if path.startswith(f"{api.PREFIX}resolve/"):
            host = path.split("host=")[1]
            if host in self.hosts:
                return self.json({"key": self.hosts[host], "version": 1})
            return self.json({"detail": "nicht gefunden"}, 404)
        if path.startswith("/media/"):
            return api.Response(200, PNG, "image/png")
        if not path.startswith(prefix):
            return self.json({}, 404)
        rest = path[len(prefix) :]
        if method == "POST":
            self.posts.append((rest, data))
            if rest == "preview/":
                if data.get("token") == "gut":
                    return self.json(
                        {"session": self.preview_session, "until": "2099-01-01T00:00:00Z"}
                    )
                return self.json({"detail": "ungültig"}, 403)
            return self.json({}, 405)
        hidden = self.maintenance and not ok_preview
        if rest.startswith("design/") and rest.endswith("/"):
            package = self.packages.get(rest[len("design/") : -1])
            return self.json(package) if package else self.json({"detail": "nicht gefunden"}, 404)
        if rest == "":
            if hidden:
                return self.json(
                    {
                        **{
                            k: self.info[k] for k in ("name", "theme", "logo_url", "allow_indexing")
                        },
                        "state": "maintenance",
                        "preview": False,
                        "maintenance_text": "Bald geht es los.",
                    },
                    503,
                )
            return self.json(
                {
                    **self.info,
                    "preview": ok_preview,
                    "state": "maintenance" if self.maintenance else "public",
                }
            )
        if rest == "imprint/":
            return self.json(
                {
                    "unit": self.info["name"],
                    "owner": self.info["name"],
                    "inherited": False,
                    "mode": "own",
                    "external_url": "",
                    "details": {
                        "name": self.info["name"],
                        "legal_form": "",
                        "address": {
                            "street": "Dorfstraße 1",
                            "postal_code": "12345",
                            "city": "Musterdorf",
                            "country": "DE",
                        },
                        "representatives": [{"name": "Max Muster", "role": "1. Vorsitzender"}],
                        "representatives_text": "",
                        "email": "info@musterdorf.example",
                        "phone": "",
                        "website": "",
                        "register_court": "Amtsgericht Musterstadt",
                        "register_number": "VR 1234",
                        "vat_id": "",
                        "responsible": "Max Muster",
                        "data_protection_officer": "",
                        "extra_text": "",
                    },
                    "privacy": {
                        "mode": "text",
                        "text": "## Datenschutz\n\nWir speichern wenig.",
                        "url": "",
                        "generated_at": "2026-10-01T10:00:00Z",
                    },
                }
            )
        files = (
            rest.startswith("images/")
            or rest.startswith("photos/")
            or rest.startswith("honors/photos/")
            or rest.startswith("statute/preview/")
        )
        if hidden:
            # Wie HUBIplan: Dateien einer verborgenen Webseite gibt es nicht
            return self.json({"detail": "nicht gefunden"}, 404 if files else 503)
        # Weitere Antworten setzen Tests über ``antworten`` (Pfad mit oder ohne Abfrage)
        extra = self.antworten.get(rest, self.antworten.get(rest.split("?")[0]))
        if extra is not None:
            return extra if isinstance(extra, api.Response) else self.json(extra)
        if (
            rest.startswith("images/")
            or rest.startswith("photos/")
            or rest.startswith("honors/photos/")
            or rest.startswith("statute/preview/")
            or rest.startswith("fee-rules/preview/")
            or rest.startswith("founding-deed/preview/")
            or rest.startswith("posts/images/")
        ):
            return api.Response(200, PNG, "image/png")
        table = {
            "board/": BOARD,
            "honors/": HONORS,
            "units/jaeger/": {
                **self.info["units"][0],
                "title": "Jägerzug",
                "text": "Wir sind *der* Jägerzug.",
                "roles": [],
                "social": [],
                "honors": HONORS["dignities"],
                "events_url": None,
                "posts": self.info.get("unit_posts", {"instagram": False, "facebook": False}),
            },
            "pages/geschichte/": {
                "slug": "geschichte",
                "title": "Chronik",
                "text": "Seit 1900.",
                "image": None,
                # Zeitleiste (Tests setzen sie über info["zeitleiste"])
                "timeline": self.info.get("zeitleiste", []),
                "timeline_newest_first": self.info.get("zeitleiste_neueste_oben", False),
            },
            "pages/anfahrt/": {
                "slug": "anfahrt",
                "title": "Anfahrt",
                "text": "Mit dem Bus.",
                "image": None,
            },
            "contact/": {
                "recipients": [
                    {"id": "allgemein", "name": "Verein (allgemein)"},
                    {"id": "r1" * 10, "name": "1. Vorsitzender"},
                ],
                "challenge": {
                    "token": "tok",
                    "salt": "salz",
                    "difficulty": 16,
                    "algorithm": "SHA-256",
                },
            },
        }
        base = rest.split("?")[0]
        if base == "posts/":
            if not self.info.get("blocks", {}).get("posts"):
                return self.json({"detail": "nicht gefunden"}, 404)
            query = rest.split("?", 1)[1] if "?" in rest else ""
            items = [p for p in POSTS if f"art={p['kind']}" in query or "art=" not in query]
            return self.json({"posts": items})
        if base == "events/":
            return self.json(events())
        if base.startswith("results/"):
            return self.results(base, rest)
        if base.startswith("galleries/"):
            # Galerie (Tests setzen die Antworten über info["galerie"])
            found = self.info.get("galerie", {}).get(base)
            return self.json(found) if found else self.json({"detail": "nicht gefunden"}, 404)
        if base in table:
            return self.json(table[base])
        return self.json({"detail": "nicht gefunden"}, 404)

    def results(self, base: str, rest: str):
        if not self.info.get("results_url"):
            return self.json({"detail": "nicht gefunden"}, 404)
        if base == "results/":
            if "start=1" in rest:
                d = results_detail(COMP)
                return self.json(
                    {
                        "competitions": [
                            {
                                **_comp(COMP, d["title"]),
                                "scorings": [
                                    {"scoring": "Einzel", "rows": d["scorings"][0]["rows"]}
                                ],
                                "prizes": [],
                                "version": "v1",
                            }
                        ],
                        "poll_seconds": 15,
                    }
                )
            return self.json(results_overview())
        if base == f"results/series/{SERIES}/":
            return self.json(results_series())
        for token in (COMP, LIVE):
            version = self.versions.get(token, "v1")
            if base == f"results/{token}/version/":
                return self.json({"version": version, "status": "", "final": token == COMP})
            if base == f"results/{token}/":
                return self.json(results_detail(token, version))
        return self.json({"detail": "nicht gefunden"}, 404)

    @staticmethod
    def json(data, status=200):
        return api.Response(status, json.dumps(data).encode(), "application/json")
