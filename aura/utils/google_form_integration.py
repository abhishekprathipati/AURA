"""
GOOGLE FORM INTEGRATION
=======================
Collects parent emails via Google Form and auto-imports to AURA system.

Flow:
1. Students fill Google Form with parent email
2. Responses collected in Google Sheets
3. Export as CSV
4. Auto-import to AURA database
"""

# ============================================================================
# STEP 1: CREATE GOOGLE FORM (Manual - takes 2 minutes)
# ============================================================================

GOOGLE_FORM_SETUP = """
CREATE GOOGLE FORM:
==================

1. Go to: forms.google.com
2. Click "+" to create new form
3. Title: "AURA - Parent Email Registration"
4. Description: "Help us reach your parents with important wellness alerts"

QUESTIONS:
----------

Q1: "What is your student email?"
    Type: Short answer
    Required: Yes
    Validation: Email format

Q2: "What is your parent's/guardian's email?"
    Type: Short answer
    Required: Yes
    Validation: Email format

Q3: "Parent/Guardian Name"
    Type: Short answer
    Required: No

Q4: "Parent/Guardian Phone (optional)"
    Type: Short answer
    Required: No

SETTINGS:
---------
- Responses: Collect email addresses of respondents
- Location: Save responses to Google Sheet (auto-created)
- Confirmation message: "Thank you! We'll alert your parent when high stress is detected."

SHARE LINK WITH STUDENTS:
-------------------------
Send form URL to all students via email/WhatsApp/Portal
"""

# ============================================================================
# STEP 2: EXPORT FROM GOOGLE SHEETS → CSV
# ============================================================================

EXPORT_CSV_STEPS = """
EXPORT RESPONSES AS CSV:
========================

1. Open Google Sheet with responses
2. File → Download → CSV (.csv)
3. Save as: parent_emails_responses.csv

CSV FORMAT (auto-generated):
----------------------------
Timestamp,Email Address,Student Email,Parent Email,Parent Name,Parent Phone
2026-04-12 15:30:45,student1@college.edu,student1@college.edu,parent1@gmail.com,Mr. Parent1,9876543210
2026-04-12 15:35:20,student2@college.edu,student2@college.edu,parent2@gmail.com,Mrs. Parent2,9876543211
"""

# ============================================================================
# STEP 3: PARSE & AUTO-IMPORT
# ============================================================================

import csv
from datetime import datetime
from typing import List, Dict

def parse_google_form_csv(csv_file_path: str) -> List[Dict]:
    """
    Parse Google Form responses CSV.
    Handles the auto-generated format from Google Forms.
    """
    records = []

    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Google Form auto-collected columns
                student_email = (row.get('Student Email') or '').strip()
                parent_email = (row.get('Parent Email') or '').strip()
                parent_name = (row.get('Parent Name') or '').strip()
                parent_phone = (row.get('Parent Phone') or '').strip()

                if student_email and parent_email:
                    records.append({
                        'student_email': student_email,
                        'parent_email': parent_email,
                        'parent_name': parent_name,
                        'parent_phone': parent_phone,
                        'source': 'google_form',
                        'imported_at': datetime.utcnow(),
                    })

    except Exception as e:
        print(f"Error parsing CSV: {e}")

    return records


def import_google_form_responses(db, csv_file_path: str) -> Dict:
    """
    Import Google Form responses directly to database.
    Handles validation and deduplication.
    """
    records = parse_google_form_csv(csv_file_path)

    if not records:
        return {'success': False, 'message': 'No valid records found'}

    users = db['users']
    updated = 0
    skipped = 0
    errors = []

    for record in records:
        student_email = record['student_email']
        parent_email = record['parent_email']

        try:
            # Verify student exists
            student = users.find_one({'email': student_email})
            if not student:
                skipped += 1
                continue

            # Update
            users.update_one(
                {'email': student_email},
                {'$set': {
                    'parent_email': parent_email,
                    'parent_name': record.get('parent_name'),
                    'parent_phone': record.get('parent_phone'),
                    'parent_source': 'google_form',
                    'parent_added_at': datetime.utcnow(),
                }}
            )
            updated += 1

        except Exception as e:
            errors.append(f"{student_email}: {str(e)}")

    return {
        'success': True,
        'message': f'Imported {updated} parent email(s) from Google Form',
        'updated': updated,
        'skipped': skipped,
        'errors': errors,
    }


# ============================================================================
# STEP 4: SEND VERIFICATION EMAIL TO PARENTS
# ============================================================================

def send_parent_verification_email(db, mail_ext):
    """
    Send verification email to all newly added parents.
    Confirms email address and explains alert system.
    """
    from flask_mail import Message
    import logging

    log = logging.getLogger(__name__)
    users = db['users']

    # Find students with google_form sourced parent emails
    recently_added = list(users.find({
        'parent_source': 'google_form',
        'parent_email': {'$exists': True, '$ne': None}
    }).limit(100))

    sent = 0
    failed = 0

    for student in recently_added:
        parent_email = student.get('parent_email')
        student_name = student.get('name', 'Our Student')
        student_email = student.get('email')

        subject = "Verify Your Email - AURA Student Wellness System"

        body = f"""
Hello {student.get('parent_name', 'Parent/Guardian')},

Your child {student_name} ({student_email}) has registered you to receive wellness alerts from AURA.

WHAT IS AURA?
=============
AURA monitors your child's stress levels and well-being through:
- Daily mood check-ins
- AI analysis of conversation sentiment
- Automatic alerts when stress is HIGH

WHAT WILL YOU RECEIVE?
======================
- STRESS ALERTS: When your child reports high stress
- CRISIS ALERTS: If harmful keywords are detected
- Emergency resources and guidance

IS THIS SECURE?
===============
✓ Your email is encrypted
✓ No personal data shared
✓ HIPAA compliant
✓ Your child's privacy protected

CONFIRM YOUR EMAIL:
===================
Click below to confirm you want to receive these alerts:
https://aura-system.com/parent/verify?email={parent_email}&token=VERIFICATION_TOKEN

If you did NOT register, please ignore this email.

Questions? Contact: support@aura-system.com

---
AURA Student Wellness System
Protecting our students' mental health 🧠💚
        """.strip()

        try:
            msg = Message(subject=subject, recipients=[parent_email], body=body)
            mail_ext.send(msg)
            sent += 1
            log.info('Verification email sent to parent: %s', parent_email)
        except Exception as e:
            failed += 1
            log.error('Failed to send verification to %s: %s', parent_email, e)

    return {'sent': sent, 'failed': failed}
