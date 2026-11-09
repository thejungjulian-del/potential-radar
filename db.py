"""SQLite storage for Potential Radar (radar.db, WAL mode).

Two tables:
  artists   — one row per artist (static-ish profile info)
  snapshots — a time series of follower/popularity/score readings per artist
"""

import json
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "radar.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    """Create tables + index if they don't exist. Safe to call repeatedly."""
    conn = _conn()
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS artists (
                id          TEXT PRIMARY KEY,
                name        TEXT,
                genres      TEXT,      -- json array
                image       TEXT,
                url         TEXT,
                first_seen  REAL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                artist_id   TEXT,
                scan_time   REAL,
                followers   INTEGER,
                popularity  INTEGER,
                score       INTEGER,
                momentum    INTEGER
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_snap_artist_time "
            "ON snapshots(artist_id, scan_time)"
        )
        conn.commit()
    finally:
        conn.close()


def upsert_artist(a):
    """Insert or update an artist's profile. first_seen is set once, on first insert."""
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO artists (id, name, genres, image, url, first_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                genres=excluded.genres,
                image=excluded.image,
                url=excluded.url
            """,
            (
                a["id"],
                a.get("name", ""),
                json.dumps(a.get("genres", [])),
                a.get("image", ""),
                a.get("url", ""),
                a.get("first_seen"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def add_snapshot(s):
    """Append a time-series reading for an artist."""
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO snapshots
                (artist_id, scan_time, followers, popularity, score, momentum)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                s["artist_id"],
                s["scan_time"],
                s["followers"],
                s["popularity"],
                s["score"],
                s["momentum"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def prev_snapshot(artist_id, before):
    """Latest snapshot for an artist STRICTLY before `before` (for momentum)."""
    conn = _conn()
    try:
        row = conn.execute(
            """
            SELECT * FROM snapshots
            WHERE artist_id = ? AND scan_time < ?
            ORDER BY scan_time DESC
            LIMIT 1
            """,
            (artist_id, before),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def latest(limit=100):
    """Latest snapshot per artist joined to artist info, ranked by score desc."""
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT a.id, a.name, a.genres, a.image, a.url,
                   s.followers, s.popularity, s.score, s.momentum, s.scan_time
            FROM artists a
            JOIN snapshots s ON s.artist_id = a.id
            JOIN (
                SELECT artist_id, MAX(scan_time) AS mt
                FROM snapshots GROUP BY artist_id
            ) m ON m.artist_id = s.artist_id AND m.mt = s.scan_time
            ORDER BY s.score DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["genres"] = json.loads(d["genres"]) if d["genres"] else []
            except (ValueError, TypeError):
                d["genres"] = []
            out.append(d)
        return out
    finally:
        conn.close()


def last_scan():
    """Timestamp of the most recent snapshot anywhere, or None if no scans yet."""
    conn = _conn()
    try:
        row = conn.execute("SELECT MAX(scan_time) AS mt FROM snapshots").fetchone()
        return row["mt"] if row and row["mt"] else None
    finally:
        conn.close()
