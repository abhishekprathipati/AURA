# AURA Database Migration Strategy

> **FIX #12**: Documentation for database schema evolution.

## Current State

AURA uses MongoDB (schema-less), so migrations are about **ensuring indexes, adding fields, and transforming data** rather than DDL changes.

## Migration Approach

### Index Management
Indexes are currently created via `_ensure_indexes()` in `utils/database.py` on every startup. For production:

```bash
# Run index creation as a one-off command instead of on every startup
python -c "from utils.database import get_db, _ensure_indexes; db = get_db(); _ensure_indexes(db)"
```

### Field Migrations

When adding a new field to an existing collection:

```python
# Example: Adding user_id UUID to all existing users
from utils.database import get_db
import uuid

db = get_db()
for user in db['users'].find({'user_id': {'$exists': False}}):
    db['users'].update_one(
        {'_id': user['_id']},
        {'$set': {'user_id': str(uuid.uuid4())}}
    )
```

### Migration Scripts

Store migration scripts in `scripts/migrations/`:

```
scripts/
├── cleanup.py           # Data retention (already exists)
└── migrations/
    ├── 001_add_user_id.py
    ├── 002_add_timezone_offset.py
    └── README.md
```

Each migration script should:
1. Be idempotent (safe to run multiple times)
2. Log its progress
3. Support `--dry-run` flag
4. Check if migration already applied before running

### Future: mongomigrate or migrate-mongo

For a more structured approach, consider:
- **mongomigrate** (Python): `pip install mongomigrate`
- **migrate-mongo** (Node.js): `npm install -g migrate-mongo`

These tools provide versioned migrations with up/down support.
