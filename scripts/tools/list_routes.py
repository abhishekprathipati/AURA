"""List all registered Flask routes."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import app

with app.app_context():
    rules = sorted(app.url_map.iter_rules(), key=lambda r: r.rule)
    for rule in rules:
        if 'activity' in rule.rule or 'log' in rule.rule:
            print(f"  >>> {rule.rule:50s} {','.join(rule.methods)}")
    print(f"\nTotal routes: {len(list(app.url_map.iter_rules()))}")
    # Show all /proctor/api routes
    print("\nAll /proctor/api routes:")
    for rule in rules:
        if rule.rule.startswith('/proctor/api'):
            print(f"  {rule.rule:50s} {','.join(rule.methods)}")
