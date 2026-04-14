"""
BULK PARENT EMAIL UPLOAD - CSV Importer
========================================
Upload CSV with student-parent email mappings.
"""

import csv
import logging
from datetime import datetime
from typing import List, Dict, Tuple

log = logging.getLogger(__name__)

def validate_email(email: str) -> bool:
    """Basic email validation"""
    if not email or '@' not in email or '.' not in email:
        return False
    return True


def load_parent_mappings_from_csv(csv_file_path: str) -> Tuple[List[Dict], List[str]]:
    """
    Load parent email mappings from CSV file.

    CSV Format:
        student_email,parent_email,parent_name,parent_phone
        student@school.edu,parent@gmail.com,Parent Name,9876543210

    Returns:
        (valid_records, errors)
    """
    valid_records = []
    errors = []

    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            if not reader.fieldnames or not all(col in reader.fieldnames for col in ['student_email', 'parent_email']):
                errors.append("CSV must have columns: student_email, parent_email")
                return valid_records, errors

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (accounting for header)
                student_email = (row.get('student_email') or '').strip()
                parent_email = (row.get('parent_email') or '').strip()
                parent_name = (row.get('parent_name') or '').strip()
                parent_phone = (row.get('parent_phone') or '').strip()

                # Validate
                if not student_email:
                    errors.append(f"Row {row_num}: Missing student_email")
                    continue

                if not parent_email:
                    errors.append(f"Row {row_num}: Missing parent_email")
                    continue

                if not validate_email(student_email):
                    errors.append(f"Row {row_num}: Invalid student_email format: {student_email}")
                    continue

                if not validate_email(parent_email):
                    errors.append(f"Row {row_num}: Invalid parent_email format: {parent_email}")
                    continue

                valid_records.append({
                    'student_email': student_email,
                    'parent_email': parent_email,
                    'parent_name': parent_name,
                    'parent_phone': parent_phone,
                })

    except FileNotFoundError:
        errors.append(f"CSV file not found: {csv_file_path}")
    except Exception as e:
        errors.append(f"Error reading CSV: {str(e)}")

    return valid_records, errors


def import_parent_emails_to_db(db, csv_file_path: str) -> Dict:
    """
    Import parent emails from CSV and update database.

    Returns: {
        'success': bool,
        'total_processed': int,
        'updated': int,
        'skipped': int,
        'errors': List[str]
    }
    """
    records, csv_errors = load_parent_mappings_from_csv(csv_file_path)

    if not records:
        return {
            'success': False,
            'total_processed': 0,
            'updated': 0,
            'skipped': 0,
            'errors': csv_errors or ['No valid records found in CSV'],
        }

    users = db['users']
    updated = 0
    skipped = 0
    errors = list(csv_errors)

    for record in records:
        student_email = record['student_email']
        parent_email = record['parent_email']
        parent_name = record.get('parent_name')
        parent_phone = record.get('parent_phone')

        try:
            # Check if student exists
            student = users.find_one({'email': student_email})

            if not student:
                errors.append(f"Student not found: {student_email} (skipped)")
                skipped += 1
                continue

            # Update student with parent info
            result = users.update_one(
                {'email': student_email},
                {'$set': {
                    'parent_email': parent_email,
                    'parent_name': parent_name,
                    'parent_phone': parent_phone,
                    'parent_added_at': datetime.utcnow(),
                }}
            )

            if result.modified_count > 0:
                updated += 1
                log.info('Updated parent for %s: %s', student_email, parent_email)
            else:
                skipped += 1

        except Exception as e:
            errors.append(f"Error updating {student_email}: {str(e)}")

    return {
        'success': len(errors) == len(csv_errors),  # Success if no new errors
        'total_processed': len(records),
        'updated': updated,
        'skipped': skipped,
        'errors': errors,
    }


def create_sample_csv(output_path: str):
    """Create a sample CSV file for reference."""
    sample_data = [
        ['student_email', 'parent_email', 'parent_name', 'parent_phone'],
        ['arjun.kumar@student.edu', 'arjun.parent@gmail.com', 'Mr. Arjun Kumar', '9876543210'],
        ['anjali.gupta@student.edu', 'anjali.parent@gmail.com', 'Mrs. Anjali Gupta', '9876543211'],
        ['vikram.joshi@student.edu', 'vikram.parent@gmail.com', 'Mr. Vikram Joshi', '9876543212'],
        ['neha.kapoor@student.edu', 'neha.parent@gmail.com', 'Mrs. Neha Kapoor', '9876543213'],
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(sample_data)

    log.info('Sample CSV created: %s', output_path)
