import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app
from utils.database import get_db

with app.app_context():
    db = get_db()
    email = '22mh1a4257@acoe.edu.in'
    phone = '6301846505'
    roll = '22MH1A4257'
    
    # 1. Update the student account with the phone and roll number
    result = db['users'].update_one(
        {'email': email}, 
        {'$set': {
            'parent_phone': phone,
            'roll_number': roll
        }}
    )
    
    # 2. Add an academic record so the parent dashboard has some data to show
    db['academic_records'].update_one(
        {'student_roll': roll},
        {'$set': {
            'student_roll': roll,
            'semester': 'Semester 6',
            'sgpa': 8.8,
            'cgpa': 8.6,
            'attendance': 94,
            'backlogs': 0,
            'credits_earned': 120,
            'total_credits': 120
        }},
        upsert=True
    )
    
    print(f"Set parent_phone='{phone}' and roll_number='{roll}' for {email}")
