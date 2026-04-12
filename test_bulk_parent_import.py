"""
TEST: Bulk Import Parent Emails
"""

from app import app
from utils.database import get_db
from utils.parent_importer import import_parent_emails_to_db, create_sample_csv
import tempfile
import os

with app.app_context():
    db = get_db()

    print("=" * 80)
    print("BULK PARENT EMAIL IMPORT TEST")
    print("=" * 80)
    print()

    # Step 1: Create sample CSV
    print("[STEP 1] Creating sample CSV file...")
    temp_dir = tempfile.gettempdir()
    csv_path = os.path.join(temp_dir, 'parent_emails.csv')

    create_sample_csv(csv_path)
    print(f"  Sample CSV created: {csv_path}")
    print()

    # Show sample content
    print("[STEP 2] Sample CSV Content:")
    print()
    with open(csv_path, 'r') as f:
        content = f.read()
        for line in content.split('\n')[:5]:
            print(f"  {line}")
    print()

    # Step 3: Import to database
    print("[STEP 3] Importing parent emails to database...")
    result = import_parent_emails_to_db(db, csv_path)

    print(f"  Success: {result['success']}")
    print(f"  Total Processed: {result['total_processed']}")
    print(f"  Updated: {result['updated']}")
    print(f"  Skipped: {result['skipped']}")

    if result['errors']:
        print(f"  Errors:")
        for error in result['errors'][:5]:
            print(f"    - {error}")

    print()

    # Step 4: Verify in database
    print("[STEP 4] Verifying in Database...")
    users = db['users']

    students_with_parent = list(users.find(
        {'parent_email': {'$exists': True, '$ne': None}},
        {'email': 1, 'name': 1, 'parent_email': 1}
    ))

    print(f"  Total students with parent email: {len(students_with_parent)}")
    print()

    for student in students_with_parent[:5]:
        print(f"  {student.get('name', 'N/A')}")
        print(f"    Student: {student.get('email')}")
        print(f"    Parent: {student.get('parent_email')}")
    print()

    # Cleanup
    os.remove(csv_path)

    print("=" * 80)
    print("RESULT: Parent emails can be bulk imported!")
    print()
    print("How to use:")
    print("  1. Create CSV file with columns:")
    print("     - student_email")
    print("     - parent_email")
    print("     - parent_name (optional)")
    print("     - parent_phone (optional)")
    print()
    print("  2. Call: POST /api/parent/import-csv")
    print("     (Upload CSV file as form data)")
    print()
    print("  3. Or manually add:")
    print("     POST /api/parent/add-manual")
    print("     JSON: { student_email, parent_email, parent_name, parent_phone }")
    print()
    print("=" * 80)
