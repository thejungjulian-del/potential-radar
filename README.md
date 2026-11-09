# Potential Radar

A radar for emerging artists that ranks them by breakout potential instead of current size. It finds Spotify artists under 250k followers and gives each one a 0–100 score that blends three signals: momentum (growth since the last scan), how popular they are for their size, and raw buzz. Each scan adds a snapshot, so growth builds into a history over time.

## Run it

```
cp .env.example .env   # optional: add a free Spotify Client ID and Secret
bash run.sh            # makes a venv, installs Flask, serves http://127.0.0.1:8799
```

To get a key, create an app at https://developer.spotify.com/dashboard. It uses Spotify's app-only Client Credentials flow for public catalog data, so there's no user login. With a key, click "Scan now" on the dashboard.

## Status

Demo mode. Without a Spotify key it shows sample data, and the artists in `mock.py` are made up. Momentum only appears after a second scan, and the score is a heuristic I picked, not something tested against artists who actually broke out.

Portfolio: https://thejungjulian-del.github.io/portfolio/
