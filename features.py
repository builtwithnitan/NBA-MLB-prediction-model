"""
src/features.py  —  Steps 6 & 7  (V3 — Statistical upgrade)

Changes from V2:
  - Added recent form fields: recent_hr_5g, recent_pa_5g (from stats layer)
  - Added hit prediction inputs: avg, obp, k_pct, contact_pct, sp_whip, sp_avg_allowed
  - Added team runs inputs: team_ops, sp_era, bullpen_era, is_home
  - All V2 fields preserved unchanged — no removals

Upstream data required (from stats.py):
  - hitter_stats now expected to carry: avg, obp, k_pct, contact_pct,
    recent_hr_5g, recent_pa_5g (falls back to defaults if missing)
  - pitcher_stats now expected to carry: era, whip, avg_allowed (falls back)
"""

import logging
import pandas as pd
from src.lineups import get_expected_pa
from src.parks   import lookup

log = logging.getLogger(__name__)

LG_HR9    = 1.15
LG_BARREL = 8.6

# Hit-model league averages
LG_K_PCT       = 22.0
LG_CONTACT_PCT = 78.0
LG_WHIP        = 1.30
LG_AVG_ALLOWED = 0.250
LG_OBP         = 0.320
LG_AVG         = 0.250

# Run-model league averages
LG_TEAM_OPS    = 0.720
LG_ERA         = 4.20
LG_BULLPEN_ERA = 4.20


def build_features(
    games:         list[dict],
    lineups:       dict,
    hitter_stats:  dict,
    pitcher_stats: dict,
    weather:       dict,
    parks:         dict,
) -> pd.DataFrame:
    """
    Merge all sources into the feature table the model needs.
    V3: adds hit-prediction and team-runs columns alongside all V2 columns.
    """
    game_map = {g["game_id"]: g for g in games}
    rows = []

    for game_id, lineup in lineups.items():
        g = game_map.get(game_id)
        if not g:
            continue

        venue       = g.get("venue", "")
        park_factor = lookup(venue, parks)
        wx          = weather.get(game_id, {})
        wx_combined = wx.get("combined_factor", 1.00)

        # Home team flag lookup
        home_team = g.get("home_team_abbr", "")

        for h in lineup:
            side = h["side"]
            pid  = h["player_id"]

            opp_pid  = g.get("home_pitcher_id")  if side == "away" else g.get("away_pitcher_id")
            opp_name = g.get("home_pitcher_name") if side == "away" else g.get("away_pitcher_name")
            if not opp_pid:
                continue

            hs = hitter_stats.get(pid)  or {}
            ps = pitcher_stats.get(opp_pid) or {}

            # ── Pitcher factor (V2 — unchanged) ───────────────────────────
            sp_hr9    = ps.get("hr9",           LG_HR9)
            sp_barrel = ps.get("sp_barrel_pct", LG_BARREL)
            pitcher_factor = 0.4 * (sp_hr9 / LG_HR9) + 0.6 * (sp_barrel / LG_BARREL)

            # ── Platoon advantage (V2 — unchanged) ────────────────────────
            bats   = h.get("bats", "R")
            throws = ps.get("throws", "R")
            platoon = _platoon(bats, throws)

            # ── V3 NEW: Team context ───────────────────────────────────────
            is_home     = (h["team_abbr"] == home_team)
            team_ops    = hs.get("team_ops",    LG_TEAM_OPS)   # enriched by stats layer
            bullpen_era = g.get("bullpen_era",  LG_BULLPEN_ERA) # from game dict if available
            sp_era      = ps.get("era",         LG_ERA)
            sp_whip     = ps.get("whip",        LG_WHIP)
            sp_avg_all  = ps.get("avg_allowed", LG_AVG_ALLOWED)

            rows.append({
                # ── Identity (V2 — unchanged) ──────────────────────────
                "player_id":        pid,
                "player_name":      h["player_name"],
                "team":             h["team_abbr"],
                "batting_order":    h["batting_order"],
                "bats":             bats,
                "game_id":          game_id,
                "venue":            venue,
                "opposing_pitcher": opp_name or "TBD",
                # ── Hitter power metrics (V2 — unchanged) ─────────────
                "barrel_pct":       hs.get("barrel_pct",    8.6),
                "hard_hit_pct":     hs.get("hard_hit_pct", 37.5),
                "fb_pct":           hs.get("fb_pct",       39.0),
                "hr_fb_pct":        hs.get("hr_fb_pct",    11.9),
                "iso":              hs.get("iso",           0.175),
                "ev":               hs.get("ev",            88.5),
                "launch_angle":     hs.get("launch_angle", 12.0),
                "pull_pct":         hs.get("pull_pct",     42.0),
                # ── Pitcher HR metrics (V2 — unchanged) ────────────────
                "sp_hr9":           sp_hr9,
                "sp_barrel_pct":    sp_barrel,
                "pitcher_factor":   round(pitcher_factor, 4),
                # ── Environment (V2 — unchanged) ──────────────────────
                "park_factor":      park_factor,
                "wx_factor":        wx_combined,
                "wind_dir":         wx.get("wind_dir", "Calm"),
                "wind_mph":         wx.get("wind_mph", 0),
                "temp_f":           wx.get("temp_f", 72),
                "indoor":           wx.get("indoor", False),
                # ── Context (V2 — unchanged) ──────────────────────────
                "expected_pa":      get_expected_pa(h["batting_order"]),
                "platoon_boost":    platoon,
                "sp_changed":       g.get("sp_changed", False),
                # ── V3 NEW: Recent form for hot-streak test ────────────
                "recent_hr_5g":     hs.get("recent_hr_5g",  0),
                "recent_pa_5g":     hs.get("recent_pa_5g",  20),
                "recent_hr_10g":    hs.get("recent_hr_10g", 0),
                "recent_pa_10g":    hs.get("recent_pa_10g", 40),
                "hr_pa_rate":       hs.get("hr_pa_rate",    0.030),
                # ── V3 NEW: Hit prediction inputs ─────────────────────
                "avg":              hs.get("avg",            LG_AVG),
                "obp":              hs.get("obp",            LG_OBP),
                "k_pct":            hs.get("k_pct",          LG_K_PCT),
                "contact_pct":      hs.get("contact_pct",    LG_CONTACT_PCT),
                "sp_whip":          sp_whip,
                "sp_avg_allowed":   sp_avg_all,
                # ── V3 NEW: Team runs inputs ──────────────────────────
                "team_ops":         team_ops,
                "sp_era":           sp_era,
                "bullpen_era":      bullpen_era,
                "is_home":          is_home,
            })

    if not rows:
        log.warning("Feature table is empty — no confirmed lineups with known pitchers")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    log.info(f"Features: {len(df)} rows built ({df['game_id'].nunique()} games)")
    return df


def _platoon(bats: str, throws: str) -> float:
    """Cross-hand matchup = slight boost. (V2 — unchanged)"""
    if bats == "S":                   return 1.00
    if bats == "L" and throws == "R": return 1.04
    if bats == "R" and throws == "L": return 1.04
    return 0.97
