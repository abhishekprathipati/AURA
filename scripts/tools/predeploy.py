"""One-command pre-deploy validation for AURA.

Usage:
  python scripts/tools/predeploy.py
  python scripts/tools/predeploy.py --base-url https://aura-mday.onrender.com
  python scripts/tools/predeploy.py --allow-dirty --skip-smoke
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
VENV_PYTHON = ROOT_DIR / '.venv' / 'Scripts' / 'python.exe'
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
CORE_TARGETS = ['app.py', 'config.py', 'models', 'routes', 'services', 'utils']


class StepFailure(RuntimeError):
    """Raised when a pre-deploy step fails."""


def run_step(name: str, command: list[str], cwd: Path = ROOT_DIR) -> None:
    print(f'\n==> {name}')
    result = subprocess.run(command, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise StepFailure(f'{name} failed with exit code {result.returncode}')


def check_git_clean(allow_dirty: bool) -> None:
    result = subprocess.run(
        ['git', 'status', '--short'],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise StepFailure('git status failed')
    if result.stdout.strip() and not allow_dirty:
        raise StepFailure('working tree is dirty; commit or stash changes, or rerun with --allow-dirty')
    print('==> git status clean' if not result.stdout.strip() else '==> git status dirty but allowed')


def main() -> int:
    parser = argparse.ArgumentParser(description='Run AURA pre-deploy checks')
    parser.add_argument('--allow-dirty', action='store_true')
    parser.add_argument('--skip-smoke', action='store_true')
    parser.add_argument('--base-url', default='')
    parser.add_argument('--skip-dedupe-check', action='store_true')
    args = parser.parse_args()

    try:
        check_git_clean(args.allow_dirty)

        run_step('ruff core lint', [PYTHON, '-m', 'ruff', 'check', *CORE_TARGETS])
        run_step('compile core modules', [PYTHON, '-m', 'compileall', *CORE_TARGETS])

        if not args.skip_dedupe_check:
            run_step('hub activity duplicate scan', [PYTHON, 'scripts/tools/dedupe_hub_activity.py', '--show', '5'])

        if not args.skip_smoke:
            if not args.base_url:
                raise StepFailure('smoke test requested but no --base-url was provided')
            run_step('deployment smoke test', [PYTHON, 'scripts/tools/smoke_test.py', '--base-url', args.base_url])

        print('\nAURA pre-deploy checks passed')
        return 0
    except StepFailure as exc:
        print(f'\nPre-deploy failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
