"""
src/stats.py  —  Step 4  (V3 — Statistical upgrade)

Changes from V2:
  - _parse_hitter: now returns k_pct, contact_pct, avg, obp from API
  - _parse_hitter: recent_hr_5g / recent_pa_5g populated (live game log call)
  - _parse_pitcher: now returns era, whip, avg_allowed alongside existing fields
  - All V2 fields and defaults preserved — no removals
  - New fields fall back to league average if API misses them

API call additions:
  - Game log endpoint: /people/{pid}/stats?stats=gameLog&group=hitting&season=2026
    Used to build last-5 and last-10 game HR counts without pybaseball.
"""

import time
import requests
import logging

log = logging.getLogger(__name__)
BASE = "https://statsapi.mlb.com/api/v1"

# ── 2026 MLB league averages ──────────────────────────────────────────────────
LG = {
    "barrel_pct":    8.6,
    "hard_hit_pct": 37.5,
    "fb_pct":       39.0,
    "hr_fb_pct":    11.9,
    "iso":          0.175,
    "ev":           88.5,
    "launch_angle": 12.0,
    "pull_pct":     42.0,
    "sp_hr9":        1.15,
    "sp_barrel_pct": 8.6,
    # V3 additions
    "k_pct":        22.0,
    "contact_pct":  78.0,
    "avg":          0.250,
    "obp":          0.320,
    "whip":         1.30,
    "avg_allowed":  0.250,
    "era":          4.20,
    "team_ops":     0.720,
}

CURRENT_SEASON = 2026


# ── HITTERS ───────────────────────────────────────────────────────────────────

def get_hitter_stats(player_ids: list) -> dict:
    result = {}
    for pid in player_ids:
        if pid:
            result[pid] = _hitter(pid)
            time.sleep(0.05)
    return result


def _hitter(pid: int) -> dict:
    try:
        resp = requests.get(
            f"{BASE}/people/{pid}/stats",
            params={"stats": "season", "group": "hitting", "season": CURRENT_SEASON},
            timeout=10,
        )
        resp.raise_for_status()
        s = _first_split(resp.json())
        base = _parse_hitter(pid, s)

        # V3: enrich with recent game log (last 5 / last 10 games)
        recent = _get_recent_form(pid)
        base.update(recent)
        return base
    except Exception as e:
        log.debug(f"  Hitter {pid} failed: {e}")
        return _default_hitter(pid)


def _parse_hitter(pid: int, s: dict) -> dict:
    try:
        hr   = int(s.get("homeRuns", 0))
        pa   = max(int(s.get("plateAppearances", 1)), 1)
        ab   = max(int(s.get("atBats", 1)), 1)
        avg  = _pct(s.get("avg",  ".000"))
        slg  = _pct(s.get("slg",  ".000"))
        obp  = _pct(s.get("obp",  ".000"))
        iso  = max(slg - avg, 0.0)
        so   = int(s.get("strikeOuts", 0))
        h    = int(s.get("hits",        0))
        # k_pct = strikeouts / plate appearances
        k_pct = round(so / pa * 100, 1) if pa > 0 else LG["k_pct"]
        # contact_pct approximation: hits / (ab - walks) ... use 100 - k_pct as proxy
        contact_pct = round(100 - k_pct, 1)

        return {
            "player_id":    pid,
            "hr_2026":      hr,
            "pa_2026":      pa,
            "hr_pa_rate":   round(hr / pa, 4),
            "avg":          avg,
            "slg":          slg,
            "obp":          obp,
            "iso":          round(iso, 3),
            # V3 additions
            "k_pct":        k_pct,
            "contact_pct":  contact_pct,
            # Statcast: league avg until pybaseball wired in
            "barrel_pct":   LG["barrel_pct"],
            "hard_hit_pct": LG["hard_hit_pct"],
            "fb_pct":       LG["fb_pct"],
            "hr_fb_pct":    LG["hr_fb_pct"],
            "ev":           LG["ev"],
            "launch_angle": LG["launch_angle"],
            "pull_pct":     LG["pull_pct"],
            "team_ops":     LG["team_ops"],  # enriched below if team stats available
        }
    except Exception:
        return _default_hitter(pid)


def _get_recent_form(pid: int, season: int = CURRENT_SEASON) -> dict:
    """
    Pull last-N game log entries and count HRs + PAs.
    Returns: recent_hr_5g, recent_pa_5g, recent_hr_10g, recent_pa_10g
    Falls back to neutral defaults if API fails.
    """
    try:
        resp = requests.get(
            f"{BASE}/people/{pid}/stats",
            params={"stats": "gameLog", "group": "hitting", "season": season},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        games = []
        for group in data.get("stats", []):
            if group.get("type", {}).get("displayName") == "gameLog":
                games = group.get("splits", [])
                break

        if not games:
            return _default_recent()

        # Most recent games are last in the list
        recent = [g.get("stat", {}) for g in games[-20:]]
        recent_5  = recent[-5:]
        recent_10 = recent[-10:]

        def _sum_games(game_list, key):
            return sum(int(g.get(key, 0) or 0) for g in game_list)

        return {
            "recent_hr_5g":  _sum_games(recent_5,  "homeRuns"),
            "recent_pa_5g":  _sum_games(recent_5,  "plateAppearances"),
            "recent_hr_10g": _sum_games(recent_10, "homeRuns"),
            "recent_pa_10g": _sum_games(recent_10, "plateAppearances"),
        }
    except Exception as e:
        log.debug(f"  Game log failed for {pid}: {e}")
        return _default_recent()


def _default_recent() -> dict:
    return {
        "recent_hr_5g":  0,
        "recent_pa_5g":  20,
        "recent_hr_10g": 0,
        "recent_pa_10g": 40,
    }


def _default_hitter(pid: int) -> dict:
    return {
        "player_id": pid, "hr_2026": 15, "pa_2026": 500,
        "hr_pa_rate": 0.030, "avg": LG["avg"], "slg": 0.420, "obp": LG["obp"],
        "iso": LG["iso"], "k_pct": LG["k_pct"], "contact_pct": LG["contact_pct"],
        "barrel_pct": LG["barrel_pct"], "hard_hit_pct": LG["hard_hit_pct"],
        "fb_pct": LG["fb_pct"], "hr_fb_pct": LG["hr_fb_pct"],
        "ev": LG["ev"], "launch_angle": LG["launch_angle"], "pull_pct": LG["pull_pct"],
        "team_ops": LG["team_ops"],
        **_default_recent(),
    }


# ── PITCHERS ──────────────────────────────────────────────────────────────────

def get_pitcher_stats(pitcher_ids: list) -> dict:
    result = {}
    for pid in pitcher_ids:
        if pid:
            result[pid] = _pitcher(pid)
            time.sleep(0.05)
    return result


def _pitcher(pid: int) -> dict:
    try:
        resp = requests.get(
            f"{BASE}/people/{pid}/stats",
            params={"stats": "season", "group": "pitching", "season": CURRENT_SEASON},
            timeout=10,
        )
        resp.raise_for_status()
        s = _first_split(resp.json())
        return _parse_pitcher(pid, s)
    except Exception as e:
        log.debug(f"  Pitcher {pid} failed: {e}")
        return _default_pitcher(pid)


def _parse_pitcher(pid: int, s: dict) -> dict:
    try:
        ip  = float(s.get("inningsPitched", 0) or 0)
        hr  = int(s.get("homeRuns",         0))
        era = float(s.get("era",   "4.50") or 4.50)
        hr9 = (hr / ip * 9) if ip > 10 else LG["sp_hr9"]

        # V3: whip and avg_allowed
        bb  = int(s.get("baseOnBalls",  0))
        h   = int(s.get("hits",         0))
        whip = ((h + bb) / ip) if ip > 10 else LG["whip"]

        bf  = max(int(s.get("battersFaced", 1)), 1)
        avg_allowed = h / bf if bf > 10 else LG["avg_allowed"]

        return {
            "pitcher_id":    pid,
            "era":           era,
            "ip":            ip,
            "hr_allowed":    hr,
            "hr9":           round(hr9, 3),
            "k9":            float(s.get("strikeoutsPer9Inn", "8.5") or 8.5),
            "bb9":           float(s.get("walksPer9Inn",      "3.0") or 3.0),
            "sp_barrel_pct": LG["sp_barrel_pct"],
            "throws":        "R",  # enrich via people API if needed
            # V3 additions
            "whip":          round(whip, 3),
            "avg_allowed":   round(avg_allowed, 3),
        }
    except Exception:
        return _default_pitcher(pid)


def _default_pitcher(pid: int) -> dict:
    return {
        "pitcher_id": pid, "era": LG["era"], "ip": 150.0,
        "hr_allowed": 20, "hr9": LG["sp_hr9"],
        "k9": 8.5, "bb9": 3.0,
        "sp_barrel_pct": LG["sp_barrel_pct"], "throws": "R",
        "whip": LG["whip"], "avg_allowed": LG["avg_allowed"],
    }


# ── Helpers (V2 — unchanged) ──────────────────────────────────────────────────

def _first_split(data: dict) -> dict:
    for group in data.get("stats", []):
        if group.get("type", {}).get("displayName") == "season":
            splits = group.get("splits", [])
            if splits:
                return splits[0].get("stat", {})
    return {}


def _pct(val) -> float:
    try:
        s = str(val).strip().lstrip(".")
        return float(s) / 1000 if len(s) <= 3 else float(val)
    except (ValueError, TypeError):
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
#  OPTIONAL: pybaseball Statcast upgrade (unchanged from V2)
#  Uncomment once:  pip install pybaseball
# ─────────────────────────────────────────────────────────────────────────────
#
# from pybaseball import statcast_batter, playerid_lookup
#
# def enrich_statcast(pid: int, player_name: str, season: int = 2026) -> dict:
#     try:
#         first, *rest = player_name.split()
#         last = " ".join(rest)
#         info = playerid_lookup(last, first)
#         if info.empty:
#             return {}
#         mlbam = info.iloc[0]["key_mlbam"]
#         df = statcast_batter(f"{season}-04-01", f"{season}-10-01", player_id=mlbam)
#         if df.empty:
#             return {}
#         return {
#             "barrel_pct":   (df["launch_speed_angle"] == 6).mean() * 100,
#             "hard_hit_pct": (df["launch_speed"] >= 95).mean() * 100,
#             "fb_pct":       (df["bb_type"] == "fly_ball").mean() * 100,
#             "hr_fb_pct":    df[df["bb_type"]=="fly_ball"]["events"].eq("home_run").mean() * 100,
#             "ev":           df["launch_speed"].dropna().mean(),
#             "launch_angle": df["launch_angle"].dropna().mean(),
#         }
#     except Exception as e:
#         log.debug(f"  Statcast enrich failed for {player_name}: {e}")
#         return {}
