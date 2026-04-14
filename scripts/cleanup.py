#!/usr/bin/env python3
"""
AURA Data Retention & Cleanup Script
=====================================

This script handles periodic cleanup of expired and old data from the AURA database.
It should be run as a scheduled task (cron job) for production deployments.

USAGE:
------
    # Run all cleanup tasks with default settings
    python scripts/cleanup.py

    # Dry run (show what would be deleted without actually deleting)
    python scripts/cleanup.py --dry-run

    # Custom retention periods
    python scripts/cleanup.py --chat-days 60 --logs-days 180

    # Verbose output
    python scripts/cleanup.py --verbose

CRON JOB SETUP (Linux/Unix):
-----------------------------
    # Edit crontab
    crontab -e

    # Add one of these entries:

    # Daily at 3 AM (recommended for production)
    0 3 * * * cd /path/to/AURA && /path/to/venv/bin/python scripts/cleanup.py >> /var/log/aura-cleanup.log 2>&1

    # Weekly on Sunday at 2 AM (lower frequency option)
    0 2 * * 0 cd /path/to/AURA && /path/to/venv/bin/python scripts/cleanup.py >> /var/log/aura-cleanup.log 2>&1

WINDOWS TASK SCHEDULER:
------------------------
    1. Open Task Scheduler
    2. Create Basic Task > Name: "AURA Data Cleanup"
    3. Trigger: Daily at 3:00 AM
    4. Action: Start a program
       - Program: C:\\path\\to\\venv\\Scripts\\python.exe
       - Arguments: scripts\\cleanup.py
       - Start in: C:\\path\\to\\AURA
    5. Finish and enable the task

ENVIRONMENT VARIABLES:
-----------------------
    DATA_RETENTION_CHAT_DAYS  - Days to keep chat messages (default: 90)
    DATA_RETENTION_LOGS_DAYS  - Days to keep stress/mood logs (default: 365)

WHAT GETS CLEANED:
-------------------
    1. Expired OTPs (already past expiration timestamp)
    2. Old chat messages (older than DATA_RETENTION_CHAT_DAYS)
    3. Old stress logs (older than DATA_RETENTION_LOGS_DAYS)
    4. Old mood records (older than DATA_RETENTION_LOGS_DAYS)
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from aura.utils.database import get_db
from aura.services.otp_service import OTPService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='AURA Data Retention & Cleanup Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--chat-days',
        type=int,
        default=int(os.getenv('DATA_RETENTION_CHAT_DAYS', '90')),
        help='Days to retain chat messages (default: 90 or DATA_RETENTION_CHAT_DAYS env var)'
    )
    parser.add_argument(
        '--logs-days',
        type=int,
        default=int(os.getenv('DATA_RETENTION_LOGS_DAYS', '365')),
        help='Days to retain stress/mood logs (default: 365 or DATA_RETENTION_LOGS_DAYS env var)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    return parser.parse_args()


def cleanup_expired_otps(dry_run=False):
    """
    Delete expired OTP records.
    Uses OTPService.cleanup_expired() which removes records past their expiration time.
    """
    logger.info("Cleaning up expired OTPs...")

    if dry_run:
        # Count how many would be deleted
        db = get_db()
        count = db[OTPService.collection_name].count_documents({
            'expires_at': {'$lt': datetime.utcnow()}
        })
        logger.info(f"  [DRY RUN] Would delete {count} expired OTP records")
        return count

    deleted_count = OTPService.cleanup_expired()
    logger.info(f"  Deleted {deleted_count} expired OTP records")
    return deleted_count


def cleanup_old_chats(days, dry_run=False):
    """
    Delete chat messages older than specified days.
    Preserves recent conversation history while removing old data.
    """
    logger.info(f"Cleaning up chat messages older than {days} days...")

    db = get_db()
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # The chats collection stores conversation history
    query = {'created_at': {'$lt': cutoff_date}}

    if dry_run:
        count = db['chats'].count_documents(query)
        logger.info(f"  [DRY RUN] Would delete {count} chat records older than {cutoff_date.date()}")
        return count

    result = db['chats'].delete_many(query)
    logger.info(f"  Deleted {result.deleted_count} chat records older than {cutoff_date.date()}")
    return result.deleted_count


def cleanup_old_stress_logs(days, dry_run=False):
    """
    Delete stress log entries older than specified days.
    Stress logs track emotional analysis from chat sessions.
    """
    logger.info(f"Cleaning up stress logs older than {days} days...")

    db = get_db()
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = {'timestamp': {'$lt': cutoff_date}}

    if dry_run:
        count = db['stress_logs'].count_documents(query)
        logger.info(f"  [DRY RUN] Would delete {count} stress log records older than {cutoff_date.date()}")
        return count

    result = db['stress_logs'].delete_many(query)
    logger.info(f"  Deleted {result.deleted_count} stress log records older than {cutoff_date.date()}")
    return result.deleted_count


def cleanup_old_moods(days, dry_run=False):
    """
    Delete mood records older than specified days.
    Mood records track student mood selections over time.
    """
    logger.info(f"Cleaning up mood records older than {days} days...")

    db = get_db()
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = {'created_at': {'$lt': cutoff_date}}

    if dry_run:
        count = db['moods'].count_documents(query)
        logger.info(f"  [DRY RUN] Would delete {count} mood records older than {cutoff_date.date()}")
        return count

    result = db['moods'].delete_many(query)
    logger.info(f"  Deleted {result.deleted_count} mood records older than {cutoff_date.date()}")
    return result.deleted_count


def cleanup_old_stress_scores(days, dry_run=False):
    """
    Delete computed stress score records older than specified days.
    These are the aggregated daily stress scores stored for trend analysis.
    """
    logger.info(f"Cleaning up stress score records older than {days} days...")

    db = get_db()
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = {'created_at': {'$lt': cutoff_date}}

    if dry_run:
        count = db['stress'].count_documents(query)
        logger.info(f"  [DRY RUN] Would delete {count} stress score records older than {cutoff_date.date()}")
        return count

    result = db['stress'].delete_many(query)
    logger.info(f"  Deleted {result.deleted_count} stress score records older than {cutoff_date.date()}")
    return result.deleted_count


def main():
    """Main entry point for the cleanup script."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("AURA Data Cleanup Started")
    logger.info(f"  Timestamp: {datetime.utcnow().isoformat()}Z")
    logger.info(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info(f"  Chat retention: {args.chat_days} days")
    logger.info(f"  Logs retention: {args.logs_days} days")
    logger.info("=" * 60)

    totals = {
        'otps': 0,
        'chats': 0,
        'stress_logs': 0,
        'moods': 0,
        'stress_scores': 0
    }

    try:
        # 1. Clean up expired OTPs (these are already past their expiration)
        totals['otps'] = cleanup_expired_otps(dry_run=args.dry_run)

        # 2. Clean up old chat messages
        totals['chats'] = cleanup_old_chats(args.chat_days, dry_run=args.dry_run)

        # 3. Clean up old stress logs (emotion analysis records)
        totals['stress_logs'] = cleanup_old_stress_logs(args.logs_days, dry_run=args.dry_run)

        # 4. Clean up old mood records
        totals['moods'] = cleanup_old_moods(args.logs_days, dry_run=args.dry_run)

        # 5. Clean up old stress score records
        totals['stress_scores'] = cleanup_old_stress_scores(args.logs_days, dry_run=args.dry_run)

    except Exception as e:
        logger.error(f"Cleanup failed with error: {e}")
        sys.exit(1)

    # Summary
    total_deleted = sum(totals.values())
    logger.info("=" * 60)
    logger.info("CLEANUP SUMMARY")
    logger.info(f"  Expired OTPs: {totals['otps']}")
    logger.info(f"  Old chats: {totals['chats']}")
    logger.info(f"  Old stress logs: {totals['stress_logs']}")
    logger.info(f"  Old moods: {totals['moods']}")
    logger.info(f"  Old stress scores: {totals['stress_scores']}")
    logger.info("-" * 60)
    logger.info(f"  TOTAL: {total_deleted} records {'would be ' if args.dry_run else ''}deleted")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("This was a DRY RUN. No data was actually deleted.")
        logger.info("Remove --dry-run flag to perform actual cleanup.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
