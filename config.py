"""
config.py
All tunable parameters for the pipeline in one place.
Edit this file to adjust model behavior without touching the source code.

Changes here affect:
  - Which picks appear (thresholds)
  - How aggressive the model is (beta weights)
  - Which season's stats are used
  - Scheduling and output options
"""

# ── Data settings ─────────────────────────────────────────────────────────────
STATS_SEASON = 2025          # which season to pull for hitter/pitcher stats
MAX_API_RETRIES = 3          # retry failed API calls this many times
API_SLEEP_SEC = 0.05         # pause between API calls (be polite)

# ── Model parameters ──────────────────────────────────────────────────────────
MIN_PICK_PROB  = 15.0        # minimum HR% to include in picks list
LOWER_FALLBACK = 13.0        # fallback if nothing hits MIN_PICK_PROB
MAX_PICKS      = 8           # never output more than this many picks
CALIBRATION    = 0.80        # scalar keeps max probability ~30%

# Beta weights (logistic regression coefficients)
# Increase a weight → that feature matters more
# Set to 0.0 → ignore that feature entirely
BETA = {
    "intercept":       -3.20,
    "barrel_pct":       1.80,   # most predictive — don't lower this
    "fb_pct":           1.40,   # gates HR opportunity
    "hr_fb_pct":        1.20,
    "iso":              0.90,
    "ev":               0.80,
    "launch_angle":     0.70,
    "pitcher_factor":   1.50,   # pitcher suppression / inflation
    "park_factor":      0.60,
    "expected_pa":      0.50,
    "wx_factor":        0.40,
    "platoon_boost":    0.30,
}

# ── League averages (2025) ────────────────────────────────────────────────────
LG_AVG = {
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
}

# ── Pitcher factor blending ───────────────────────────────────────────────────
# How to combine HR/9 and barrel% allowed into a single pitcher factor.
# Must sum to 1.0.
PF_HR9_WEIGHT    = 0.40      # HR/9 weight
PF_BARREL_WEIGHT = 0.60      # barrel% allowed weight (more stable, use more)

# ── Output settings ───────────────────────────────────────────────────────────
PRINT_PICKS    = True        # print picks to console
SAVE_PICKS_CSV = True        # save to data/picks/
LOG_RUNS       = True        # append to run_log.csv

# ── Statcast settings (if pybaseball is installed) ────────────────────────────
USE_STATCAST       = False   # set True after: pip install pybaseball
STATCAST_CACHE_HRS = 20      # hours before re-fetching from Savant

# ── Scheduling hints (used by scheduler.py) ───────────────────────────────────
SCHEDULE_FULL_RUN    = "08:00"   # full pipeline (AM)
SCHEDULE_LINEUP_RUN1 = "12:00"   # lineups-only re-run (noon ET)
SCHEDULE_LINEUP_RUN2 = "15:30"   # catch late-game lineups (3:30 PM ET)

# ── V3 Statistical model settings ────────────────────────────────────────────
HOT_STREAK_PVALUE   = 0.05   # p-value threshold: below this = statistically hot
RECENT_FORM_GAMES   = 5      # primary recent-form window (also uses 10 and 20)
RECENT_FORM_MAX_ADJ = 0.15   # cap recent-form adjustment at ±15%
CI_Z_SCORE          = 1.96   # 95% confidence interval
MIN_RECENT_PA       = 5      # minimum PA in window before applying form adj

# ── Team runs model weights ────────────────────────────────────────────────────
RUNS_SP_WEIGHT      = 0.70   # SP ERA weight in combined pitcher factor
RUNS_BP_WEIGHT      = 0.30   # bullpen ERA weight
RUNS_HOME_BONUS     = 1.05   # home team runs multiplier
RUNS_AWAY_PENALTY   = 0.97   # away team runs multiplier

# ── Confidence score weights (must sum to 100) ─────────────────────────────────
CONF_CI_PTS         = 25     # points for narrow confidence interval
CONF_MATCHUP_PTS    = 25     # points for strong pitcher/park matchup
CONF_LINEUP_PTS     = 25     # points for confirmed lineup (no SP change flag)
CONF_CONSISTENCY_PTS= 25     # points for season vs recent form agreement
