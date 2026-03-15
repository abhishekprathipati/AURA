"""Deduplicate hub_activity records by user_email.

Usage:
  python scripts/tools/dedupe_hub_activity.py           # dry run
  python scripts/tools/dedupe_hub_activity.py --apply   # delete duplicates
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

from utils.database import get_db  # noqa: E402


def _sort_key(doc: Dict[str, Any]) -> Tuple[datetime, str]:
    ts = doc.get('last_active') or doc.get('updated_at') or doc.get('created_at')
    if not isinstance(ts, datetime):
        ts = datetime.min
    return ts, str(doc.get('_id', ''))


def find_duplicates() -> Tuple[int, int, List[Dict[str, Any]]]:
    db = get_db()
    coll = db['hub_activity']

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for doc in coll.find({}, {'user_email': 1, 'last_active': 1, 'updated_at': 1, 'created_at': 1}):
        email = (doc.get('user_email') or '').strip()
        if not email:
            continue
        grouped[email].append(doc)

    duplicate_users = 0
    duplicate_docs = 0
    plans: List[Dict[str, Any]] = []

    for email, docs in grouped.items():
        if len(docs) <= 1:
            continue
        duplicate_users += 1
        docs_sorted = sorted(docs, key=_sort_key, reverse=True)
        keep_doc = docs_sorted[0]
        remove_docs = docs_sorted[1:]
        duplicate_docs += len(remove_docs)
        plans.append(
            {
                'email': email,
                'keep_id': keep_doc.get('_id'),
                'remove_ids': [d.get('_id') for d in remove_docs],
            }
        )

    return duplicate_users, duplicate_docs, plans


def apply_cleanup(plans: List[Dict[str, Any]]) -> int:
    db = get_db()
    coll = db['hub_activity']

    removed = 0
    for plan in plans:
        remove_ids = [rid for rid in plan.get('remove_ids', []) if rid is not None]
        if not remove_ids:
            continue
        res = coll.delete_many({'_id': {'$in': remove_ids}})
        removed += int(res.deleted_count)
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description='Deduplicate hub_activity by user_email')
    parser.add_argument('--apply', action='store_true', help='Actually delete duplicate records')
    parser.add_argument('--show', type=int, default=10, help='Number of duplicate users to preview')
    args = parser.parse_args()

    dup_users, dup_docs, plans = find_duplicates()

    print(f'duplicate_users={dup_users}')
    print(f'duplicate_docs={dup_docs}')

    for plan in plans[: max(0, args.show)]:
        print(f"email={plan['email']} keep={plan['keep_id']} remove_count={len(plan['remove_ids'])}")

    if not args.apply:
        print('dry_run=true (use --apply to delete duplicates)')
        return 0

    removed = apply_cleanup(plans)
    print(f'removed_docs={removed}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
