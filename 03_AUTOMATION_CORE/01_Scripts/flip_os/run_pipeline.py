#!/usr/bin/env python3
"""
Flip OS -- Full Pipeline Runner
Runs scraper -> scorer -> brief in sequence.
Designed for cron: 5:00 AM PT daily.
"""
import logging
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [FlipOS] %(message)s")
log = logging.getLogger("flip_os.pipeline")

def main():
    log.info("=" * 60)
    log.info("FLIP OS DAILY PIPELINE")
    log.info("=" * 60)

    # Step 1: Scrape for penny items
    log.info("\n[1/3] Running penny scraper...")
    from penny_scraper import run_scraper
    items = run_scraper()
    log.info("Scraper found %d items", len(items))

    # Brief pause to avoid rate limiting on searches
    time.sleep(5)

    # Step 2: Score demand
    log.info("\n[2/3] Running demand scorer...")
    from demand_scorer import run_scorer
    scored = run_scorer(hours_back=48)
    log.info("Scored %d items", len(scored))

    time.sleep(2)

    # Step 3: Generate daily brief
    log.info("\n[3/3] Generating daily brief...")
    from daily_brief import generate_brief
    brief = generate_brief()

    log.info("\n" + "=" * 60)
    log.info("PIPELINE COMPLETE")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
