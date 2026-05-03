"""Google Maps Platform helpers — Geocoding, Directions, Places.

These tools degrade gracefully when GOOGLE_MAPS_API_KEY is unset (local
hermetic tests). When the key is missing we return an `ok` envelope with
synthetic values + a `degraded` flag so the agent prompt can disclose
honestly to the user.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from tools._envelope import ok

log = logging.getLogger(__name__)


def _client():
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        return None
    try:
        import googlemaps  # noqa: WPS433
        return googlemaps.Client(key=key, timeout=8)
    except Exception:
        log.exception("googlemaps client init failed")
        return None


def get_directions(origin: str, destination: str, mode: str = "walking") -> dict:
    if mode not in ("walking", "transit", "driving", "bicycling"):
        mode = "walking"
    client = _client()
    if client is None:
        return ok(
            degraded=True,
            mode=mode,
            distance_text="—", duration_text="—",
            deeplink=_maps_deeplink(origin, destination),
            note="Maps API key not configured; returning a Google Maps deeplink only.",
        )
    try:
        results = client.directions(origin, destination, mode=mode)
        if not results:
            return ok(degraded=False, mode=mode, distance_text="—", duration_text="—",
                      deeplink=_maps_deeplink(origin, destination), note="no_route")
        leg = results[0]["legs"][0]
        return ok(
            degraded=False,
            mode=mode,
            distance_text=leg["distance"]["text"],
            duration_text=leg["duration"]["text"],
            distance_meters=leg["distance"]["value"],
            duration_seconds=leg["duration"]["value"],
            deeplink=_maps_deeplink(origin, destination),
        )
    except Exception as e:
        log.warning("directions failed: %s", e)
        return ok(degraded=True, mode=mode, distance_text="—", duration_text="—",
                  deeplink=_maps_deeplink(origin, destination))


def nearest_landmarks(lat: float, lng: float, limit: int = 3) -> dict:
    client = _client()
    if client is None:
        return ok(degraded=True, landmarks=[])
    try:
        resp = client.places_nearby(location=(lat, lng), radius=500, type="point_of_interest")
        names = [
            p.get("name") for p in resp.get("results", [])[:limit] if p.get("name")
        ]
        return ok(degraded=False, landmarks=names)
    except Exception as e:
        log.warning("places nearby failed: %s", e)
        return ok(degraded=True, landmarks=[])


def _maps_deeplink(origin: str, destination: str) -> str:
    from urllib.parse import quote_plus
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(origin)}"
        f"&destination={quote_plus(destination)}"
        "&travelmode=walking"
    )
