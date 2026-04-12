"""
PARENT EMAIL MANAGEMENT ENDPOINT
=================================
API route to bulk upload/manage parent emails for students.
"""

from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from utils.database import get_db
from utils.parent_importer import import_parent_emails_to_db, create_sample_csv
from utils.auth_helpers import login_required
import os
import tempfile
import logging

parent_bp = Blueprint('parent_mgmt', __name__, url_prefix='/api/parent')
log = logging.getLogger(__name__)

UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_FILES = {'csv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_FILES


@parent_bp.route('/import-csv', methods=['POST'])
@login_required
def import_parent_emails():
    """
    Bulk import parent emails from CSV file.

    Requires admin/proctor role.

    Form Data:
        file: CSV file with columns (student_email, parent_email, parent_name, parent_phone)
    """
    # Check authorization (proctor or hod)
    user_role = session.get('user_role')
    if user_role not in ('proctor', 'hod', 'admin'):
        return jsonify({'error': 'Unauthorized - requires proctor/HOD access'}), 403

    # Check file provided
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only CSV files allowed'}), 400

    try:
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(temp_path)

        # Import to database
        db = get_db()
        result = import_parent_emails_to_db(db, temp_path)

        # Clean up
        os.remove(temp_path)

        # Log activity
        log.info('Parent email import: updated=%d (%s)', result['updated'], session.get('user_email'))

        return jsonify({
            'success': result['success'],
            'message': f"Imported {result['updated']} parent email(s)",
            'stats': {
                'total_processed': result['total_processed'],
                'updated': result['updated'],
                'skipped': result['skipped'],
            },
            'errors': result['errors'][:10],  # Return first 10 errors only
        }), 200

    except Exception as e:
        log.error('Parent import failed: %s', e)
        return jsonify({'error': f'Import failed: {str(e)}'}), 500


@parent_bp.route('/add-manual', methods=['POST'])
@login_required
def add_parent_email_manual():
    """
    Manually add/update parent email for a single student.

    JSON:
        {
            "student_email": "student@school.edu",
            "parent_email": "parent@gmail.com",
            "parent_name": "Parent Name",
            "parent_phone": "9876543210"
        }
    """
    # Check authorization
    user_role = session.get('user_role')
    if user_role not in ('proctor', 'hod', 'admin', 'student'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    student_email = (data.get('student_email') or '').strip()
    parent_email = (data.get('parent_email') or '').strip()
    parent_name = (data.get('parent_name') or '').strip()
    parent_phone = (data.get('parent_phone') or '').strip()

    # Validate
    if not student_email or '@' not in student_email:
        return jsonify({'error': 'Invalid student_email'}), 400

    if not parent_email or '@' not in parent_email:
        return jsonify({'error': 'Invalid parent_email'}), 400

    # Check authorization: students can only update their own; proctors can update anyone
    if user_role == 'student':
        if session.get('user_email') != student_email:
            return jsonify({'error': 'Cannot update other students'}), 403

    try:
        db = get_db()
        users = db['users']

        # Check if student exists
        student = users.find_one({'email': student_email})
        if not student:
            return jsonify({'error': f'Student not found: {student_email}'}), 404

        # Update
        result = users.update_one(
            {'email': student_email},
            {'$set': {
                'parent_email': parent_email,
                'parent_name': parent_name,
                'parent_phone': parent_phone,
                'parent_added_at': __import__('datetime').datetime.utcnow(),
            }}
        )

        if result.modified_count > 0:
            log.info('Parent email added for %s: %s', student_email, parent_email)
            return jsonify({
                'success': True,
                'message': f'Parent email updated for {student_email}',
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'No changes made',
            }), 200

    except Exception as e:
        log.error('Failed to add parent email: %s', e)
        return jsonify({'error': f'Update failed: {str(e)}'}), 500


@parent_bp.route('/list', methods=['GET'])
@login_required
def list_parents():
    """
    List all students and their parent emails (proctor/HOD only).
    """
    # Check authorization
    user_role = session.get('user_role')
    if user_role not in ('proctor', 'hod', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        db = get_db()
        users = db['users']

        # Get all students with parent info
        students = list(users.find(
            {'role': 'student'},
            {
                'email': 1,
                'name': 1,
                'department': 1,
                'parent_email': 1,
                'parent_name': 1,
                'parent_phone': 1,
            }
        ).sort('name', 1))

        # Count
        total = len(students)
        with_parent = sum(1 for s in students if s.get('parent_email'))
        without_parent = total - with_parent

        return jsonify({
            'success': True,
            'summary': {
                'total_students': total,
                'with_parent_email': with_parent,
                'without_parent_email': without_parent,
                'coverage_percent': round((with_parent / total * 100) if total > 0 else 0, 1),
            },
            'students': students,
        }), 200

    except Exception as e:
        log.error('Failed to list parents: %s', e)
        return jsonify({'error': f'Query failed: {str(e)}'}), 500


@parent_bp.route('/sample-csv', methods=['GET'])
def download_sample_csv():
    """
    Generate and download a sample CSV template.
    """
    try:
        from flask import send_file
        import tempfile

        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_path = temp_file.name
        temp_file.close()

        # Create sample
        create_sample_csv(temp_path)

        return send_file(
            temp_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name='parent_emails_template.csv'
        )

    except Exception as e:
        log.error('Failed to generate CSV: %s', e)
        return jsonify({'error': f'Failed: {str(e)}'}), 500
