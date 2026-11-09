"""Run a scan: discover emerging artists, score them, persist a snapshot each."""

import time

import db
import discovery
import scoring
import spotify


def run(genres=None):
    """Discover + score emerging artists and store a snapshot for each.

    Returns {"scanned": n, "scan_time": t} on success,
    or {"error": "..."} if Spotify credentials are missing.
    """
    if not spotify.enabled():
        return {
            "error": "Spotify key not set. Add SPOTIFY_CLIENT_ID and "
            "SPOTIFY_CLIENT_SECRET to .env to go live."
        }

    db.init()
    scan_time = time.time()
    found = discovery.emerging(genres=genres)

    scanned = 0
    for a in found:
        prev = db.prev_snapshot(a["id"], scan_time)
        cur = {
            "followers": a["followers"],
            "popularity": a["popularity"],
            "scan_time": scan_time,
        }
        sc, mom = scoring.score(cur, prev)

        a.setdefault("first_seen", scan_time)
        db.upsert_artist(a)
        db.add_snapshot(
            {
                "artist_id": a["id"],
                "scan_time": scan_time,
                "followers": a["followers"],
                "popularity": a["popularity"],
                "score": sc,
                "momentum": mom,
            }
        )
        scanned += 1

    return {"scanned": scanned, "scan_time": scan_time}


if __name__ == "__main__":
    print(run())
