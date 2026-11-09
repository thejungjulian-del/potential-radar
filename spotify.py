"""Spotify Web API client using the Client Credentials flow (app-only, no user login).

Only the Python standard library is used for HTTP. The app's only pip dependency is Flask.
Credentials come from env vars SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET.
"""

import base64
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

# cached access token: {"token": str, "expires_at": float}
_token_cache = {"token": None, "expires_at": 0.0}


def enabled():
    """True only when both Spotify credentials are present in the environment."""
    return bool(os.environ.get("SPOTIFY_CLIENT_ID")) and bool(
        os.environ.get("SPOTIFY_CLIENT_SECRET")
    )


def _get_token():
    """Fetch (and cache) an app-only access token via the Client Credentials flow."""
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=data,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode())

    token = payload["access_token"]
    expires_in = payload.get("expires_in", 3600)
    # refresh a minute early to be safe
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + expires_in - 60
    return token


def _get(path, params=None):
    """GET a Spotify API path with retry on 429 (rate limit) and 5xx.

    Respects the Retry-After header. Returns parsed JSON or {} on persistent failure.
    """
    url = f"{API_BASE}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    attempts = 0
    while attempts < 5:
        attempts += 1
        token = _get_token()
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {token}"}, method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = int(e.headers.get("Retry-After", "1") or "1")
                time.sleep(min(retry_after, 30))
                continue
            if e.code == 401:
                # token may have expired; force refresh and retry once
                _token_cache["token"] = None
                continue
            if 500 <= e.code < 600:
                time.sleep(min(2 ** attempts, 20))
                continue
            # other client errors are not retryable
            return {}
        except (urllib.error.URLError, TimeoutError):
            time.sleep(min(2 ** attempts, 20))
            continue
    return {}


def new_release_artist_ids(limit=50, country="US"):
    """Artist IDs that appear on Spotify's new-album releases (a strong 'fresh' signal)."""
    ids = []
    data = _get(
        "/browse/new-releases",
        {"limit": min(limit, 50), "country": country},
    )
    for album in (data.get("albums", {}) or {}).get("items", []) or []:
        for artist in album.get("artists", []) or []:
            aid = artist.get("id")
            if aid:
                ids.append(aid)
    return ids


def search_artist_ids(query, limit=50):
    """Artist IDs from a catalog search (supports genre: filters like genre:pop)."""
    ids = []
    data = _get(
        "/search",
        {"q": query, "type": "artist", "limit": min(limit, 50)},
    )
    for artist in (data.get("artists", {}) or {}).get("items", []) or []:
        aid = artist.get("id")
        if aid:
            ids.append(aid)
    return ids


def playlist_artist_ids(playlist_id, limit=100):
    """Artist IDs from the tracks of an editorial playlist (e.g. Fresh Finds)."""
    ids = []
    data = _get(
        f"/playlists/{playlist_id}/tracks",
        {"limit": min(limit, 100), "fields": "items(track(artists(id)))"},
    )
    for item in data.get("items", []) or []:
        track = (item or {}).get("track") or {}
        for artist in track.get("artists", []) or []:
            aid = artist.get("id")
            if aid:
                ids.append(aid)
    return ids


def artists(ids):
    """Fetch full artist objects for the given IDs (batched 50 at a time, deduped).

    Returns a list of dicts {id,name,followers,popularity,genres,image,url},
    robust to missing fields.
    """
    seen = []
    out = []
    for aid in ids:
        if aid and aid not in seen:
            seen.append(aid)

    for i in range(0, len(seen), 50):
        batch = seen[i : i + 50]
        data = _get("/artists", {"ids": ",".join(batch)})
        for a in data.get("artists", []) or []:
            if not a:
                continue
            images = a.get("images") or []
            image = images[0].get("url", "") if images else ""
            followers = ((a.get("followers") or {}).get("total")) or 0
            out.append(
                {
                    "id": a.get("id", ""),
                    "name": a.get("name", "Unknown"),
                    "followers": int(followers),
                    "popularity": int(a.get("popularity") or 0),
                    "genres": a.get("genres") or [],
                    "image": image,
                    "url": (a.get("external_urls") or {}).get("spotify", ""),
                }
            )
    return out
