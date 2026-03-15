#!/usr/bin/env python
"""
seed_hub.py — Standalone Connect Hub seed script.

Run once (or when the hub collections are empty) to populate realistic
demo data: peer users, connections, groups, events, resources, and feed.

Usage
─────
    python scripts/tools/seed_hub.py                       # dry-run check
    python scripts/tools/seed_hub.py --seed                # actually seed
    python scripts/tools/seed_hub.py --seed --force        # re-seed even if data exists

This is intentionally a separate script rather than auto-run inside a route,
because database seeding is a deployment/admin concern, not a request concern.
"""

import argparse
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# ── Bootstrap Flask app context so we can use get_db() ──────────────────────
ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402  (app-level import after sys.path fix)
from utils.database import get_db  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Seed data
# ─────────────────────────────────────────────────────────────────────────────

SEED_PEERS = [
    {'name': 'Arjun Kumar',   'email': 'arjun.kumar@student.edu',   'dept': 'Computer Science',        'year': 3, 'stress': 62, 'trend': 'stable'},
    {'name': 'Priya Sharma',  'email': 'priya.sharma@student.edu',  'dept': 'Computer Science',        'year': 2, 'stress': 45, 'trend': 'decreasing'},
    {'name': 'Sneha Patel',   'email': 'sneha.patel@student.edu',   'dept': 'Biology',                 'year': 4, 'stress': 71, 'trend': 'increasing'},
    {'name': 'Meera Reddy',   'email': 'meera.reddy@student.edu',   'dept': 'Electrical Engineering',  'year': 3, 'stress': 58, 'trend': 'stable'},
    {'name': 'Kavya Singh',   'email': 'kavya.singh@student.edu',   'dept': 'Mechanical Engineering',  'year': 2, 'stress': 39, 'trend': 'stable'},
    {'name': 'Ravi Verma',    'email': 'ravi.verma@student.edu',    'dept': 'Mathematics',             'year': 3, 'stress': 55, 'trend': 'decreasing'},
    {'name': 'Anjali Gupta',  'email': 'anjali.gupta@student.edu',  'dept': 'Computer Science',        'year': 4, 'stress': 68, 'trend': 'increasing'},
    {'name': 'Rohit Rao',     'email': 'rohit.rao@student.edu',     'dept': 'Physics',                 'year': 2, 'stress': 42, 'trend': 'stable'},
    {'name': 'Divya Nair',    'email': 'divya.nair@student.edu',    'dept': 'Biology',                 'year': 3, 'stress': 64, 'trend': 'increasing'},
    {'name': 'Vikram Joshi',  'email': 'vikram.joshi@student.edu',  'dept': 'Electrical Engineering',  'year': 4, 'stress': 73, 'trend': 'stable'},
    {'name': 'Neha Kapoor',   'email': 'neha.kapoor@student.edu',   'dept': 'Computer Science',        'year': 2, 'stress': 38, 'trend': 'decreasing'},
    {'name': 'Amit Desai',    'email': 'amit.desai@student.edu',    'dept': 'Mechanical Engineering',  'year': 3, 'stress': 51, 'trend': 'stable'},
    {'name': 'Pooja Iyer',    'email': 'pooja.iyer@student.edu',    'dept': 'Mathematics',             'year': 4, 'stress': 66, 'trend': 'increasing'},
    {'name': 'Karan Mehta',   'email': 'karan.mehta@student.edu',   'dept': 'Physics',                 'year': 2, 'stress': 44, 'trend': 'stable'},
    {'name': 'Sanya Bansal',  'email': 'sanya.bansal@student.edu',  'dept': 'Biology',                 'year': 3, 'stress': 59, 'trend': 'decreasing'},
]

PEER_CONNECTIONS = [
    ('arjun.kumar@student.edu',  'anjali.gupta@student.edu'),
    ('priya.sharma@student.edu', 'neha.kapoor@student.edu'),
    ('sneha.patel@student.edu',  'divya.nair@student.edu'),
    ('meera.reddy@student.edu',  'vikram.joshi@student.edu'),
    ('kavya.singh@student.edu',  'amit.desai@student.edu'),
    ('ravi.verma@student.edu',   'pooja.iyer@student.edu'),
]

SEED_GROUPS = [
    {'name': 'AI Study Circle',    'type': 'study',        'desc': 'Discuss ML, deep learning, and AI papers.',
     'members': ['arjun.kumar@student.edu', 'anjali.gupta@student.edu', 'neha.kapoor@student.edu']},
    {'name': 'Exam Prep Squad',    'type': 'study',        'desc': 'Collaborate on upcoming exam preparation.',
     'members': ['priya.sharma@student.edu', 'ravi.verma@student.edu', 'karan.mehta@student.edu']},
    {'name': 'Mindful Moments',    'type': 'relaxation',   'desc': 'Daily meditation and breathing exercises.',
     'members': ['sneha.patel@student.edu', 'divya.nair@student.edu', 'sanya.bansal@student.edu']},
    {'name': 'Stress Busters',     'type': 'peer_support', 'desc': 'Share strategies and support each other.',
     'members': ['meera.reddy@student.edu', 'vikram.joshi@student.edu', 'pooja.iyer@student.edu']},
    {'name': 'Code & Chill',       'type': 'relaxation',   'desc': 'Casual coding sessions with zero pressure.',
     'members': ['arjun.kumar@student.edu', 'neha.kapoor@student.edu', 'rohit.rao@student.edu']},
    {'name': 'Campus Wellness Club','type': 'peer_support', 'desc': 'Mental health awareness and peer support.',
     'members': ['kavya.singh@student.edu', 'amit.desai@student.edu', 'sanya.bansal@student.edu']},
    {'name': 'Physics Problem Solving','type': 'study',    'desc': 'Work through challenging physics problems.',
     'members': ['rohit.rao@student.edu', 'karan.mehta@student.edu']},
]

SEED_EVENTS = [
    {'title': 'Guided Meditation Session', 'type': 'meditation', 'days': 2, 'dur': 30,
     'desc': 'Calming 30-minute guided meditation.',
     'participants': ['sneha.patel@student.edu', 'divya.nair@student.edu', 'kavya.singh@student.edu']},
    {'title': 'Stress Management Workshop', 'type': 'workshop', 'days': 5, 'dur': 60,
     'desc': 'Proven techniques to manage academic stress.',
     'participants': ['meera.reddy@student.edu', 'pooja.iyer@student.edu']},
    {'title': 'Study Techniques Webinar', 'type': 'webinar', 'days': 7, 'dur': 45,
     'desc': 'Evidence-based study methods.',
     'participants': ['arjun.kumar@student.edu', 'priya.sharma@student.edu', 'ravi.verma@student.edu']},
    {'title': 'Yoga & Breathing', 'type': 'meditation', 'days': 3, 'dur': 45,
     'desc': 'Gentle yoga session suitable for all levels.',
     'participants': ['sanya.bansal@student.edu', 'amit.desai@student.edu']},
    {'title': 'Peer Support Circle', 'type': 'peer_support', 'days': 4, 'dur': 60,
     'desc': 'Safe space to share experiences.',
     'participants': ['vikram.joshi@student.edu', 'karan.mehta@student.edu']},
]

SEED_RESOURCES = [
    {'title': 'Pomodoro Timer Guide',    'link': 'https://todoist.com/productivity-methods/pomodoro-technique',
     'tags': ['study', 'productivity'],  'desc': 'Boost focus with 25-minute work sessions',
     'liked': ['arjun.kumar@student.edu', 'priya.sharma@student.edu', 'ravi.verma@student.edu']},
    {'title': 'Headspace Basics',        'link': 'https://www.headspace.com/meditation/meditation-for-beginners',
     'tags': ['wellness', 'meditation'], 'desc': 'Introduction to mindfulness meditation',
     'liked': ['sneha.patel@student.edu', 'kavya.singh@student.edu']},
    {'title': 'Khan Academy CS',         'link': 'https://www.khanacademy.org/computing',
     'tags': ['study', 'cs'],            'desc': 'Free computer science courses and tutorials',
     'liked': ['neha.kapoor@student.edu', 'anjali.gupta@student.edu']},
    {'title': 'Breathing Exercise App',  'link': 'https://apps.apple.com',
     'tags': ['wellness', 'stress'],     'desc': 'Quick breathing techniques for stress relief',
     'liked': ['meera.reddy@student.edu', 'divya.nair@student.edu', 'sanya.bansal@student.edu']},
    {'title': 'Study Music Playlist',    'link': 'https://open.spotify.com/playlist/37i9dQZF1DX8NTLI2TtZa6',
     'tags': ['study', 'focus'],         'desc': 'Lo-fi beats for concentration',
     'liked': ['rohit.rao@student.edu', 'karan.mehta@student.edu']},
    {'title': 'Mental Health Toolkit',   'link': 'https://www.nimh.nih.gov/health/topics/caring-for-your-mental-health',
     'tags': ['wellness', 'mental-health'], 'desc': 'Resources from NIMH for mental wellness',
     'liked': ['vikram.joshi@student.edu', 'pooja.iyer@student.edu', 'amit.desai@student.edu']},
]


# ─────────────────────────────────────────────────────────────────────────────
# Core seed function (no Flask session dependency)
# ─────────────────────────────────────────────────────────────────────────────

def seed_hub(db, force: bool = False) -> dict[str, int]:
    """Seed the Connect Hub collections.

    Returns a dict with counts of inserted documents per collection.
    """
    if not force and db['groups'].count_documents({}) > 0:
        print("Hub already seeded (groups collection is non-empty). Re-run with --force to override.")
        return {}

    now = datetime.utcnow()
    counts: dict[str, int] = {}

    from werkzeug.security import generate_password_hash

    # ── 1. Peer users ──────────────────────────────────────────────────────────
    for peer in SEED_PEERS:
        if not db['users'].find_one({'email': peer['email']}):
            db['users'].insert_one({
                'email': peer['email'],
                'name': peer['name'],
                'password': generate_password_hash('demo123'),
                'role': 'student',
                'department': peer['dept'],
                'year': peer['year'],
                'created_at': now - timedelta(days=30),
            })
        db['stress'].insert_one({
            'user_email': peer['email'],
            'score': peer['stress'],
            'trend': peer['trend'],
            'confidence': round(0.75 + 0.15 * peer['stress'] / 100, 4),
            'created_at': now - timedelta(hours=2),
        })
    peer_emails = [p['email'] for p in SEED_PEERS]
    counts['users'] = len(peer_emails)
    counts['stress'] = len(peer_emails)

    # Every 3rd user gets an online activity marker
    for i, email in enumerate(peer_emails):
        if i % 3 == 0:
            db['hub_activity'].insert_one({'user_email': email, 'last_active': now - timedelta(minutes=2)})

    # ── 2. Peer connections ────────────────────────────────────────────────────
    for u1, u2 in PEER_CONNECTIONS:
        db['connections'].insert_one({
            'user_email': u1, 'connected_to': u2,
            'status': 'accepted', 'created_at': now - timedelta(days=5),
        })
    counts['connections'] = len(PEER_CONNECTIONS)

    # ── 3. Groups ──────────────────────────────────────────────────────────────
    group_ids: dict[str, str] = {}
    for g in SEED_GROUPS:
        gid = str(uuid.uuid4())
        group_ids[g['name']] = gid
        db['groups'].insert_one({
            'group_id': gid, 'name': g['name'], 'description': g['desc'],
            'type': g['type'], 'created_by': g['members'][0],
            'members': g['members'], 'member_count': len(g['members']),
            'created_at': now - timedelta(days=10), 'updated_at': now - timedelta(hours=3),
        })
    counts['groups'] = len(SEED_GROUPS)

    # ── 4. Group messages ──────────────────────────────────────────────────────
    if 'AI Study Circle' in group_ids:
        gid = group_ids['AI Study Circle']
        msgs = [
            ('arjun.kumar@student.edu',  'Anyone read the new Attention is All You Need paper?', 120),
            ('anjali.gupta@student.edu', 'Yes! The transformer architecture is fascinating.',      115),
            ('neha.kapoor@student.edu',  "Can we discuss it in tomorrow's session?",               110),
        ]
        for email, text, ago in msgs:
            u = db['users'].find_one({'email': email}, {'name': 1})
            db['group_messages'].insert_one({
                'group_id': gid, 'sender_email': email,
                'sender_name': u['name'] if u else email.split('@')[0],
                'message': text, 'created_at': now - timedelta(minutes=ago),
            })
    counts['group_messages'] = 3

    # ── 5. Events ──────────────────────────────────────────────────────────────
    for ev in SEED_EVENTS:
        db['events'].insert_one({
            'event_id': str(uuid.uuid4()), 'title': ev['title'],
            'description': ev['desc'],
            'date': now + timedelta(days=ev['days']),
            'duration_minutes': ev['dur'], 'type': ev['type'],
            'created_by': ev['participants'][0],
            'participants': ev['participants'], 'max_participants': 50,
            'created_at': now - timedelta(days=2),
        })
    counts['events'] = len(SEED_EVENTS)

    # ── 6. Resources ───────────────────────────────────────────────────────────
    for r in SEED_RESOURCES:
        db['resources'].insert_one({
            'resource_id': str(uuid.uuid4()), 'title': r['title'],
            'link': r['link'], 'description': r['desc'],
            'uploaded_by': r['liked'][0] if r['liked'] else 'system',
            'tags': r['tags'], 'likes': len(r['liked']), 'liked_by': r['liked'],
            'created_at': now - timedelta(hours=24),
        })
    counts['resources'] = len(SEED_RESOURCES)

    # ── 7. Activity feed ───────────────────────────────────────────────────────
    feed_items = [
        ('arjun.kumar@student.edu',  'created_group',  'AI Study Circle',            10),
        ('priya.sharma@student.edu', 'joined_group',   'Exam Prep Squad',             8),
        ('sneha.patel@student.edu',  'created_event',  'Guided Meditation Session',   6),
        ('ravi.verma@student.edu',   'shared_resource','Pomodoro Timer Guide',         5),
        ('meera.reddy@student.edu',  'joined_event',   'Stress Management Workshop',  4),
        ('kavya.singh@student.edu',  'shared_resource','Breathing Exercise App',       3),
        ('anjali.gupta@student.edu', 'created_group',  'Code & Chill',                2),
        ('neha.kapoor@student.edu',  'joined_group',   'AI Study Circle',             1),
    ]
    for email, action, target, ago in feed_items:
        u = db['users'].find_one({'email': email}, {'name': 1})
        db['hub_feed'].insert_one({
            'actor_name': u['name'] if u else email.split('@')[0],
            'actor_email': email, 'action': action, 'target': target,
            'created_at': now - timedelta(hours=ago),
        })
    counts['hub_feed'] = len(feed_items)

    return counts


# ─────────────────────────────────────────────────────────────────────────────
# CLI entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed the AURA Connect Hub with demo data")
    parser.add_argument('--seed',  action='store_true', help='Actually write to the database (default: dry-run)')
    parser.add_argument('--force', action='store_true', help='Re-seed even if data already exists')
    args = parser.parse_args()

    if not args.seed:
        print("Dry-run mode: pass --seed to actually seed, --force to re-seed existing data.")
        print()

    app = create_app()
    with app.app_context():
        db = get_db()
        groups_count = db['groups'].count_documents({})
        print(f"Current groups count: {groups_count}")

        if not args.seed:
            print("Dry-run complete. No changes made.")
            return

        counts = seed_hub(db, force=args.force)
        if counts:
            print("\nSeed complete:")
            for col, n in counts.items():
                print(f"  {col}: {n} inserted")
        else:
            print("Nothing seeded (use --force to override).")


if __name__ == '__main__':
    main()
