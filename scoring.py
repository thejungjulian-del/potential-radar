"""Potential Score: how much BREAKOUT POTENTIAL an emerging artist has (0-100).

The score blends three 0-100 signals:
  underrated — high popularity on a SMALL follower base (the core 'hidden gem' signal)
  buzz       — raw popularity (catalog heat right now)
  momentum   — growth per day vs the previous snapshot (only when we have history)
"""

import math


def _underrated(popularity, followers):
    """High popularity relative to a small audience => underrated/hidden gem.

    pop / log10(followers+10) is large when popularity is decent but followers are tiny.
    We normalize that ratio onto a 0-100 scale. A brand-new artist (~10 followers) with
    popularity ~40 lands high; a 200k-follower artist with the same popularity lands low.
    """
    ratio = popularity / math.log10(followers + 10)
    # ratio roughly spans 0..40 in practice (pop up to 100, log10 of small base ~1..2).
    # Scale so a strong hidden gem approaches 100, then clamp.
    return max(0.0, min(100.0, ratio * 2.5))


def _momentum(cur, prev):
    """Growth per day vs the previous snapshot, blended and clamped 0-100.

    Combines fractional follower growth/day and raw popularity points/day.
    Returns 0.0 when there is no usable previous snapshot.
    """
    if not prev:
        return 0.0

    dt_days = (cur["scan_time"] - prev["scan_time"]) / 86400.0
    if dt_days <= 0:
        return 0.0

    prev_followers = max(prev.get("followers", 0), 1)
    follower_growth_per_day = (
        (cur["followers"] - prev_followers) / prev_followers
    ) / dt_days  # fractional, e.g. 0.05 = +5%/day
    pop_points_per_day = (cur["popularity"] - prev.get("popularity", 0)) / dt_days

    # Weight + rescale onto 0-100. +10%/day follower growth alone ~= 70 pts;
    # +1 popularity point/day ~= 15 pts. Tuned so steady-but-real growth is visible.
    raw = follower_growth_per_day * 700.0 + pop_points_per_day * 15.0
    return max(0.0, min(100.0, raw))


def score(cur, prev=None):
    """Return (score, momentum) — both rounded ints in 0-100.

    cur/prev are dict-like with keys: followers, popularity, scan_time.
    """
    underrated = _underrated(cur["popularity"], cur["followers"])
    buzz = float(cur["popularity"])  # already 0-100
    momentum = _momentum(cur, prev)

    if prev:
        # We have history: reward real growth most, then hidden-gem ratio, then raw buzz.
        composite = 0.42 * momentum + 0.34 * underrated + 0.24 * buzz
    else:
        # Cold start (first time we see this artist): lean on underrated + buzz.
        composite = 0.62 * underrated + 0.38 * buzz

    composite = max(0.0, min(100.0, composite))
    return round(composite), round(momentum)
