#!/usr/bin/env python3
"""
run_pipeline.py  —  Main entry point
Run this file to execute the full MLB HR prediction pipeline.

────────────────────────────────────────────────────
USAGE
────────────────────────────────────────────────────
Full pipeline (run at 8 AM):
    python run_pipeline.py

Re-run after lineups release (~noon ET):
    python run_pipeline.py --lineups-only

Run for a specific past date (backtesting):
    python run_pipeline.py --date 2026-04-01

Record actual results after games:
    python run_pipeline.py --record "Kyle Schwarber" --hit
    python run_pipeline.py --record "Aaron Judge" --no-hit

Print accuracy report:
    python run_pipeline.py --accuracy
────────────────────────────────────────────────────
"""

import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

# ── Logging — writes to console AND logs/pipeline.log ─────────────────────────
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/pipeline.log", mode="a"),
    ],
)
log = logging.getLogger(__name__)

# ── Import pipeline modules ────────────────────────────────────────────────────
from src.schedule import get_todays_games
from src.pitchers import get_probable_pitchers
from src.lineups  import get_confirmed_lineups
from src.stats    import get_hitter_stats, get_pitcher_stats
from src.weather  import get_weather_factors
from src.parks    import get_park_factors
from src.features import build_features
from src.model    import run_model
from src.storage  import (save_picks, save_run_log,
                           record_result, print_accuracy_report)


def run(date: str, lineups_only: bool = False) -> None:
    div = "=" * 55
    log.info(div)
    log.info(f"  MLB HR Pipeline  —  {date}")
    log.info(div)

    # ── Step 1 ────────────────────────────────────────────────────────────────
    log.info("[ 1 ] Schedule")
    games = get_todays_games(date)
    if not games:
        log.warning("No active games today. Exiting.")
        return

    # ── Step 2 ────────────────────────────────────────────────────────────────
    log.info("[ 2 ] Checking for late SP changes")
    games = get_probable_pitchers(games)

    # ── Step 3 ────────────────────────────────────────────────────────────────
    log.info("[ 3 ] Confirmed lineups")
    lineups = get_confirmed_lineups(games)
    n_hitters = sum(len(v) for v in lineups.values())

    if n_hitters == 0:
        log.warning(
            "\n  ⏳  No lineups confirmed yet.\n"
            "  Lineups usually drop 3–4 hours before first pitch.\n"
            "  Re-run with:  python run_pipeline.py --lineups-only\n"
        )
        return

    # ── Step 4 ────────────────────────────────────────────────────────────────
    log.info("[ 4 ] Hitter and pitcher stats")
    hitter_ids  = [h["player_id"] for pl in lineups.values() for h in pl]
    pitcher_ids = list({g.get("away_pitcher_id") for g in games}
                     | {g.get("home_pitcher_id") for g in games} - {None})

    hitter_stats  = get_hitter_stats(hitter_ids)
    pitcher_stats = get_pitcher_stats(pitcher_ids)

    # ── Optional: Statcast enrichment ─────────────────────────────────────────
    # Uncomment after:  pip install pybaseball
    # from src.statcast import enrich_hitters, enrich_pitchers
    # hitter_stats  = enrich_hitters(hitter_stats, season=2025)
    # pitcher_stats = enrich_pitchers(pitcher_stats, season=2025)

    # ── Step 5 ────────────────────────────────────────────────────────────────
    log.info("[ 5 ] Weather and park factors")
    weather = get_weather_factors(games)
    parks   = get_park_factors()

    # ── Steps 6 & 7 ───────────────────────────────────────────────────────────
    log.info("[ 6 ] Merging data")
    log.info("[ 7 ] Building features")
    features = build_features(games, lineups, hitter_stats, pitcher_stats, weather, parks)
    if features.empty:
        log.warning("Feature table is empty. Exiting.")
        return

    # ── Step 8 ────────────────────────────────────────────────────────────────
    log.info("[ 8 ] Running model")
    picks = run_model(features)

    # ── Step 9 ────────────────────────────────────────────────────────────────
    log.info("[ 9 ] Picks")
    _print_picks(picks, date)

    # ── Step 10 ───────────────────────────────────────────────────────────────
    log.info("[10 ] Saving to CSV")
    top_prob = picks[0]["hr_prob"] if picks else 0.0
    save_picks(picks, date)
    save_run_log(date, len(games), n_hitters, len(picks), top_prob)

    log.info("Pipeline complete.\n")


def _print_picks(picks: list[dict], date: str) -> None:
    div = "=" * 65
    print(f"\n{div}")
    print(f"  ⚾  MLB HR PICKS — {date}  [V3 Statistical Model]")
    print(div)

    if not picks:
        print("  No picks above threshold today.\n")
        print(div + "\n")
        return

    for i, p in enumerate(picks, 1):
        sp_flag  = "  ⚠ SP CHANGED — verify" if p.get("sp_changed") else ""
        hot_flag = "  🔥 STATISTICALLY HOT" if p.get("statistically_hot") else ""
        ci_warn  = "  ⚡ wide CI" if p.get("hr_ci_width", 0) > 20 else ""

        # ── Header line ────────────────────────────────────────────────
        print(f"\n  {i}.  {p['player_name']} ({p['team']}){hot_flag}")
        print(f"       vs {p['opposing_pitcher']}  |  {p['venue']}")

        # ── HR prediction ──────────────────────────────────────────────
        print(f"       HR:   {p['hr_prob']:.1f}%  "
              f"[{p['hr_ci_lo']:.1f}% – {p['hr_ci_hi']:.1f}% CI]{sp_flag}{ci_warn}")

        # ── Hit prediction ─────────────────────────────────────────────
        print(f"       Hit:  {p['hit_prob']:.1f}%  "
              f"[{p['hit_ci_lo']:.1f}% – {p['hit_ci_hi']:.1f}% CI]")

        # ── Statistical test ───────────────────────────────────────────
        hot_str = "YES" if p.get("statistically_hot") else "no"
        print(f"       p-value: {p['p_value']:.4f}  |  "
              f"Statistically hot: {hot_str}  |  "
              f"Confidence: {p['confidence_score']}/100")

        # ── Team / environment context ─────────────────────────────────
        print(f"       Exp. team runs: {p['expected_runs']:.1f}  |  "
              f"Park: {p['park_factor']:.2f}x  |  "
              f"PA: {p['expected_pa']:.1f}  |  "
              f"Wind: {p['wind_dir']} {p['wind_mph']:.0f}mph")

        # ── Key reason + plain-English explanation ─────────────────────
        print(f"       Key: {p['key_reason']}")
        print(f"       → {p['explanation']}")

        if p["risk_notes"] != "None":
            print(f"       ⚠ Risk: {p['risk_notes']}")

    print(f"\n{div}\n")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MLB HR Prediction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--date",         metavar="YYYY-MM-DD",
                        help="Run for this date (default: today)")
    parser.add_argument("--lineups-only", action="store_true",
                        help="Skip schedule/pitcher steps, re-run from lineup step")
    parser.add_argument("--record",       metavar="PLAYER_NAME",
                        help="Record actual result for a pick")
    parser.add_argument("--hit",          action="store_true",
                        help="Player homered (use with --record)")
    parser.add_argument("--no-hit",       action="store_true",
                        help="Player did not homer (use with --record)")
    parser.add_argument("--accuracy",     action="store_true",
                        help="Print accuracy report from all_picks.csv")
    args = parser.parse_args()

    if args.accuracy:
        print_accuracy_report()
        return

    date = args.date or datetime.today().strftime("%Y-%m-%d")

    if args.record:
        if not (args.hit or args.no_hit):
            print("Error: use --record with --hit or --no-hit")
            sys.exit(1)
        record_result(args.record, date, hit=args.hit)
        return

    run(date, lineups_only=args.lineups_only)


if __name__ == "__main__":
    main()
