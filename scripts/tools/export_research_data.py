import csv
import json
import os
import argparse
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

def export_data(output_format='csv', output_file=None):
    """
    Exports anonymized stress and emotion data for research purposes.
    Replaces PII (emails) with anonymous IDs and removes sensitive fields.
    """
    load_dotenv()
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/aura_db')
    client = MongoClient(mongo_uri)
    db = client.get_database()

    print(f"[*] Extracting research data from {db.name}...")

    # 1. Map emails to anonymous IDs from student_anonymity collection
    anonymity_map = {}
    anonymity_logs = db['student_anonymity'].find({})
    for entry in anonymity_logs:
        anonymity_map[entry['email']] = entry['anonymous_id']

    # 2. Extract stress logs
    stress_logs = list(db['stress_logs'].find({}).sort('timestamp', 1))
    
    anonymized_data = []
    skipped_count = 0

    for log in stress_logs:
        email = log.get('user_email')
        anon_id = anonymity_map.get(email)
        
        if not anon_id:
            skipped_count += 1
            continue

        # Extract only research-relevant fields
        record = {
            'anonymous_id': anon_id,
            'timestamp': log['timestamp'].isoformat() if isinstance(log['timestamp'], datetime) else log['timestamp'],
            'stress_score': log.get('stress_score'),
            'primary_emotion': log.get('primary_emotion'),
            'emotion_distribution': log.get('emotion_distribution', {})
        }
        anonymized_data.append(record)

    print(f"[+] Found {len(anonymized_data)} valid records (Skipped {skipped_count} without anon IDs)")

    # 3. Save to file
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"research_export_{timestamp}.{output_format}"

    if output_format == 'csv':
        keys = ['anonymous_id', 'timestamp', 'stress_score', 'primary_emotion', 'emotion_distribution']
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            # Convert dict to string for CSV compatibility
            for row in anonymized_data:
                row['emotion_distribution'] = json.dumps(row['emotion_distribution'])
                dict_writer.writerow(row)
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(anonymized_data, f, indent=2)

    print(f"[SUCCESS] Research dataset exported to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export anonymized AURA research data.")
    parser.add_argument("--format", choices=['csv', 'json'], default='csv', help="Output format (default: csv)")
    parser.add_argument("--out", help="Output file path")
    
    args = parser.parse_args()
    export_data(output_format=args.format, output_file=args.out)
