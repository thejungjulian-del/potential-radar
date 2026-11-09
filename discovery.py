"""Gather candidate EMERGING artists from several Spotify sources, then filter.

We cast a wide net (new releases + editorial discovery playlists + genre searches),
fetch full artist objects, and keep only artists that are still SMALL (low followers)
but already showing some catalog heat (nonzero popularity).
"""

import spotify

# Spotify "Fresh Finds"-family editorial playlists (emerging / undiscovered artists).
# NOTE: editorial playlist IDs change over time — Spotify reshuffles/retires them.
# New-releases + genre searches below are the robust fallback if these go stale.
FRESH_FINDS = [
    "37i9dQZF1DWWjGdmeTyeJ6",  # Fresh Finds
    "37i9dQZF1DX2Tb2kNFLBVz",  # Fresh Finds: Pop
    "37i9dQZF1DWUFAJPVM3HTX",  # Fresh Finds: Hip-Hop
    "37i9dQZF1DX6bBjHfdRnza",  # Fresh Finds: Indie
]

# Genre searches — broad fallback that always returns real catalog artists.
GENRE_QUERIES = [
    'genre:pop',
    'genre:"hip hop"',
    'genre:indie',
    'genre:"r&b"',
    'genre:afrobeats',
    'genre:hyperpop',
    'genre:electronic',
    'genre:"indie pop"',
]


def emerging(genres=None, ceiling=250000):
    """Return emerging-artist dicts (followers <= ceiling, popularity >= 8).

    genres: optional list of substrings; if given, keep only artists whose genre tags
    contain at least one of them (case-insensitive).
    """
    candidate_ids = []

    # (a) artists on brand-new releases
    try:
        candidate_ids += spotify.new_release_artist_ids(limit=50)
    except Exception:
        pass

    # (b) editorial discovery playlists (may be stale — wrapped so one bad ID is harmless)
    for pid in FRESH_FINDS:
        try:
            candidate_ids += spotify.playlist_artist_ids(pid, limit=100)
        except Exception:
            pass

    # (c) genre searches
    for q in GENRE_QUERIES:
        try:
            candidate_ids += spotify.search_artist_ids(q, limit=50)
        except Exception:
            pass

    if not candidate_ids:
        return []

    # fetch full artist objects (batched + deduped inside spotify.artists)
    try:
        full = spotify.artists(candidate_ids)
    except Exception:
        return []

    wanted = [g.lower() for g in genres] if genres else None
    out = []
    for a in full:
        if a["followers"] > ceiling:
            continue
        if a["popularity"] < 8:
            continue
        if wanted:
            tags = " ".join(a.get("genres", [])).lower()
            if not any(w in tags for w in wanted):
                continue
        out.append(a)
    return out
