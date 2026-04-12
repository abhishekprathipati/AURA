"""
COMPLETE WORKFLOW: Google Form -> CSV -> Auto-Import to AURA
===========================================================
"""

from app import app
from utils.database import get_db
from utils.google_form_integration import parse_google_form_csv, import_google_form_responses
import tempfile
import os
import csv
from datetime import datetime

with app.app_context():
    db = get_db()

    print("=" * 80)
    print("GOOGLE FORM INTEGRATION - COMPLETE WORKFLOW")
    print("=" * 80)
    print()

    # STEP 1: Create sample Google Form CSV response
    print("[STEP 1] Simulating Google Form Responses...")
    print()

    # Sample responses (as if exported from Google Sheets)
    google_form_responses = [
        {
            'Timestamp': '2026-04-12 10:00:00',
            'Email Address': 'arjun.kumar@student.edu',
            'Student Email': 'arjun.kumar@student.edu',
            'Parent Email': 'arjun.parent@gmail.com',
            'Parent Name': 'Mr. Arjun Kumar',
            'Parent Phone': '9876543210',
        },
        {
            'Timestamp': '2026-04-12 10:05:00',
            'Email Address': 'anjali.gupta@student.edu',
            'Student Email': 'anjali.gupta@student.edu',
            'Parent Email': 'anjali.parent@gmail.com',
            'Parent Name': 'Mrs. Anjali Gupta',
            'Parent Phone': '9876543211',
        },
        {
            'Timestamp': '2026-04-12 10:10:00',
            'Email Address': 'meera.reddy@student.edu',
            'Student Email': 'meera.reddy@student.edu',
            'Parent Email': 'meera.parent@gmail.com',
            'Parent Name': 'Mr. Meera Reddy',
            'Parent Phone': '9876543212',
        },
    ]

    # Create temp CSV
    temp_dir = tempfile.gettempdir()
    csv_path = os.path.join(temp_dir, 'google_form_responses.csv')

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=google_form_responses[0].keys())
        writer.writeheader()
        writer.writerows(google_form_responses)

    print(f"  Sample Google Form CSV created: {csv_path}")
    print(f"  Records in CSV: {len(google_form_responses)}")
    print()

    # Show sample content
    print("[STEP 2] CSV Content Sample:")
    print()
    with open(csv_path, 'r') as f:
        lines = f.readlines()
        for line in lines[:3]:
            print(f"  {line.strip()}")
    print()

    # STEP 3: Parse and import
    print("[STEP 3] Parsing & Importing to Database...")
    result = import_google_form_responses(db, csv_path)

    print(f"  Success: {result['success']}")
    print(f"  Message: {result['message']}")
    print(f"  Updated: {result['updated']}")
    print(f"  Skipped: {result['skipped']}")

    if result.get('errors'):
        print(f"  Errors: {result['errors']}")
    print()

    # STEP 4: Verify in database
    print("[STEP 4] Database Verification...")
    users = db['users']

    students_imported = list(users.find(
        {'parent_source': 'google_form'},
        {'email': 1, 'name': 1, 'parent_email': 1, 'parent_name': 1}
    ))

    print(f"  Students with parent emails from Google Form: {len(students_imported)}")
    print()

    for student in students_imported[:5]:
        print(f"  [OK] {student.get('name', 'N/A')}")
        print(f"    Student: {student.get('email')}")
        print(f"    Parent: {student.get('parent_email')} ({student.get('parent_name', 'N/A')})")
    print()

    # Cleanup
    os.remove(csv_path)

    # STEP 5: Overall coverage
    print("[STEP 5] Overall Parent Email Coverage:")
    total_students = users.count_documents({'role': 'student'})
    with_parent = users.count_documents({'parent_email': {'$exists': True, '$ne': None}})
    without_parent = total_students - with_parent
    coverage = (with_parent / total_students * 100) if total_students > 0 else 0

    print(f"  Total students: {total_students}")
    print(f"  With parent email: {with_parent}")
    print(f"  Without parent email: {without_parent}")
    print(f"  Coverage: {coverage:.1f}%")
    print()

    print("=" * 80)
    print("WORKFLOW COMPLETE!")
    print()
    print("HOW TO USE IN PRODUCTION:")
    print()
    print("1. CREATE GOOGLE FORM:")
    print("   - Go to forms.google.com")
    print("   - Create form with 2 questions:")
    print("     Q1: Student Email (required)")
    print("     Q2: Parent Email (required)")
    print("   - Share with all students")
    print()
    print("2. COLLECT RESPONSES (1-7 days):")
    print("   - Students fill form with parent email")
    print("   - Google automatically collects responses")
    print()
    print("3. EXPORT FROM GOOGLE SHEETS:")
    print("   - File -> Download -> CSV")
    print("   - Get: parent_emails_responses.csv")
    print()
    print("4. UPLOAD TO AURA:")
    print("   - POST /api/parent/import-csv")
    print("   - Upload CSV file")
    print("   - Auto-import to database")
    print()
    print("5. SEND VERIFICATION EMAILS:")
    print("   - Parents receive confirmation")
    print("   - They can verify their email")
    print()
    print("RESULT: All students linked to parents! ")
    print()
    print("=" * 80)
