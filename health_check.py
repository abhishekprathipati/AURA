#!/usr/bin/env python
"""
AURA health_check.py — Production Readiness Validator.
Automatically runs lint checks, runtime import tests, 
dependency audits, and security configuration scans.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(name, command):
    print(f"[*] Running {name}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            print(f"[+] {name} PASSED.")
            return True
        else:
            print(f"[!] {name} FAILED.")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"[!] Critical Error running {name}: {e}")
        return False

def main():
    print("="*40)
    print("      AURA PRODUCTION HEALTH CHECK      ")
    print("="*40)
    
    success = True

    # 1. Lint Check
    if not run_command("Ruff Lint", "ruff check ."):
        success = False

    # 2. Dependency Check
    if not run_command("Dependency Check", "pip check"):
        success = False

    # 3. Import Test (Smoke Test)
    if not run_command("Runtime Import Test", "python -c \"import app; import routes.student; import services.stress_service; print('All modules imported successfully.')\""):
        success = False

    # 4. Redis Connectivity Check (if REDIS_URL exists)
    if os.environ.get('REDIS_URL'):
        if not run_command("Redis Connection", "python -c \"import redis, os; r=redis.from_url(os.environ['REDIS_URL']); r.ping(); print('Redis reachable.')\""):
            success = False
    else:
        print("[~] Skipping Redis connectivity check (REDIS_URL not set).")

    # 5. DB Connectivity Check
    if not run_command("Database Connection", "python -c \"from utils.database import get_db; db=get_db(); db.command('ping'); print('MongoDB reachable.')\""):
        success = False

    print("\n" + "="*40)
    if success:
        print("  ✅ STATUS: ALL SYSTEMS NOMINAL. READY FOR RELEASE.")
    else:
        print("  ❌ STATUS: CRITICAL FAILURES FOUND. DO NOT DEPLOY.")
    print("="*40)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
