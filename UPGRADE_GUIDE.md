# V3 Upgrade Guide — What Changed and Where

## Install first
```
pip install -r requirements.txt
```
One new dependency: `scipy` (for binomial p-value test).

---

## Deployment: 5 files to drop into your existing pipeline

Copy these into your existing `TurnReady/mlb_pipeline/` folder.
**Everything else is untouched** — schedule, lineups, parks, weather, storage, tests, backtest, dashboard, scheduler.

| File | What changed |
|---|---|
| `src/model.py` | 7 new functions, 11 new output fields |
| `src/features.py` | 15 new columns in the feature row |
| `src/stats.py` | Game log API call, 3 new pitcher fields |
| `run_pipeline.py` | `_print_picks()` shows all V3 fields |
| `config.py` | 9 new tuning knobs at bottom of file |

---

## New output fields (per pick)

| Field | Type | Description |
|---|---|---|
| `hr_ci_lo` | float | HR probability lower bound (95% CI) |
| `hr_ci_hi` | float | HR probability upper bound (95% CI) |
| `hr_ci_width` | float | CI width — wide = low reliability |
| `hit_prob` | float | Probability of 1+ hit in this game |
| `hit_ci_lo` | float | Hit probability lower bound |
| `hit_ci_hi` | float | Hit probability upper bound |
| `p_value` | float | Binomial test p-value for hot streak |
| `statistically_hot` | bool | True if p-value < 0.05 AND recent rate > season rate |
| `expected_runs` | float | Expected team runs this game |
| `confidence_score` | int | 0–100 composite confidence score |
| `explanation` | str | Plain-English summary sentence |

---

## How the statistical tests work

### Hot streak test (null hypothesis)
- **Null hypothesis**: the player's recent HR rate equals their season baseline
- **Test**: `scipy.stats.binomtest(recent_hrs, recent_pa, season_hr_pa_rate)`
- **Result**: if p-value < 0.05 AND recent rate > baseline → `statistically_hot = True`
- **Key rule**: a player who hit a HR yesterday but has a season rate of 3% and 
  went 1-for-22 recently will NOT be marked hot — the math doesn't support it

### Confidence interval (Wilson score)
- Used instead of normal approximation — more accurate at small probabilities
- HR CI uses `cap=32.0%` (realistic max HR probability)
- Hit CI uses `cap=99.0%` (no artificial cap)
- Wide CI (>20%) → confidence score drops → `⚡ wide CI` flag in output

### Confidence score (0–100)
Four components, 25 points each:
1. **CI width**: narrow = high confidence, wide = low confidence
2. **Matchup quality**: SP HR/9 > 1.2, park > 1.05x, platoon edge
3. **Lineup confirmed**: 25pts if no SP change flag, 10pts if changed
4. **Consistency**: season HR rate vs recent form agreement

---

## Recent form: how the adjustment works

```
recent_rate = recent_hr_5g / recent_pa_5g
season_rate = hr_pa_rate (season)

p_value = binomtest(recent_hrs, recent_pa, season_rate)

if p_value < 0.10:          # significant evidence
    delta = (recent_rate - season_rate) / season_rate
    multiplier = 1.0 + clamp(delta * 0.3, -0.15, +0.15)
    adjusted_prob = base_prob * multiplier
else:
    adjusted_prob = base_prob   # no change — not significant
```

Cap: ±15% max adjustment. A player on a 3-game HR streak who has a very low 
season rate will not be blindly boosted unless the statistics support it.

---

## Hit prediction model

```
hit_rate = 0.50 * avg + 0.30 * (obp - 0.05) + 0.20 * (1 - k_pct) * contact_pct

pitcher_adj = 1.0 + (sp_whip - 1.30) * 0.20
sp_adj      = 1.0 + (sp_avg_allowed - 0.250) * 1.5

hit_rate *= pitcher_adj * sp_adj * platoon_boost

P(1+ hit) = 1 - (1 - hit_rate) ^ expected_pa
```

---

## Team runs model

```
ops_factor      = team_ops / 0.720
era_factor      = opp_era / 4.20        # high ERA = hittable
bp_factor       = bullpen_era / 4.20
pitcher_factor  = 0.70 * era_factor + 0.30 * bp_factor

expected_runs   = 4.50
                * ops_factor
                * pitcher_factor
                * park_factor
                * wx_factor
                * (1.05 if home else 0.97)
```

---

## Sample console output (V3)

```
=================================================================
  ⚾  MLB HR PICKS — 2026-04-07  [V3 Statistical Model]
=================================================================

  1.  Shohei Ohtani (LAD)  🔥 STATISTICALLY HOT
       vs Kevin Gausman  |  Rogers Centre
       HR:   27.0%  [18.2% – 35.8% CI]
       Hit:  85.2%  [71.7% – 92.9% CI]
       p-value: 0.0312  |  Statistically hot: YES  |  Confidence: 71/100
       Exp. team runs: 5.2  |  Park: 1.01x  |  PA: 4.3  |  Wind: Calm 0mph
       Key: barrel% 29.4 | platoon edge
       → Shohei is a strong HR candidate today. elite barrel rate (29.4%).
         statistically hot streak confirmed (p=0.031).

  2.  Yordan Alvarez (HOU)
       vs Kyle Freeland  |  Coors Field
       HR:   27.0%  [18.5% – 35.5% CI]
       Hit:  87.3%  [74.1% – 94.2% CI]
       p-value: 0.6261  |  Statistically hot: no  |  Confidence: 66/100
       Exp. team runs: 7.0  |  Park: 1.35x  |  PA: 4.3  |  Wind: Out 8mph
       Key: barrel% 21.4 | HR-prone SP (HR/9=1.42) | park 1.35x
       → Yordan has a solid shot at going deep. facing a HR-prone pitcher.
         Coors Field is the key environment factor.
```

---

## What was NOT changed

These files are **identical to V2** — do not replace them:
- `src/schedule.py`
- `src/pitchers.py`  
- `src/lineups.py`
- `src/parks.py`
- `src/weather.py`
- `src/statcast.py`
- `src/storage.py`
- `backtest.py`
- `dashboard.py`
- `scheduler.py`
- `tests/test_pipeline.py`

---

## Tuning in config.py

```python
HOT_STREAK_PVALUE   = 0.05   # lower = stricter hot flag
RECENT_FORM_MAX_ADJ = 0.15   # cap form multiplier at ±15%
CI_Z_SCORE          = 1.96   # 1.645 for 90% CI, 2.576 for 99% CI
RUNS_SP_WEIGHT      = 0.70   # SP ERA weight in team runs model
RUNS_BP_WEIGHT      = 0.30   # bullpen ERA weight
```
