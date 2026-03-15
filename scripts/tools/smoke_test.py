"""Production smoke tests for AURA.

Usage:
  python scripts/tools/smoke_test.py --base-url https://aura-mday.onrender.com
  python scripts/tools/smoke_test.py --base-url http://127.0.0.1:5000 --email student@aura.edu --password password123
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict

import requests

DEFAULT_TIMEOUT = 90
RETRYABLE_STATUSES = {502, 503, 504}
DEFAULT_EMAIL = os.getenv('AURA_SMOKE_EMAIL', 'student@aura.edu')
DEFAULT_PASSWORD = os.getenv('AURA_SMOKE_PASSWORD', 'password123')


class SmokeFailure(RuntimeError):
    """Raised when a smoke-test step fails."""


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def _print_step(name: str, details: str) -> None:
    print(f'[PASS] {name}: {details}')


def _get_json(response: requests.Response) -> Dict[str, Any]:
    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise SmokeFailure(f'Expected JSON response from {response.url}, got invalid JSON') from exc


def _request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    *,
    retries: int = 4,
    sleep_seconds: float = 3.0,
    **kwargs: Any,
) -> requests.Response:
    last_response: requests.Response | None = None
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = session.request(method, url, timeout=DEFAULT_TIMEOUT, **kwargs)
            if response.status_code not in RETRYABLE_STATUSES:
                return response
            last_response = response
        except requests.RequestException as exc:
            last_error = exc

        if attempt < retries:
            time.sleep(sleep_seconds)

    if last_response is not None:
        return last_response
    if last_error is not None:
        raise last_error
    raise SmokeFailure(f'No response returned for {url}')


def run_smoke(base_url: str, email: str, password: str, skip_chat: bool = False, live_chat: bool = False) -> None:
    base_url = base_url.rstrip('/')
    session = requests.Session()
    session.headers.update({'User-Agent': 'AURA-SmokeTest/1.0'})

    health = _request_with_retry(session, 'GET', f'{base_url}/health')
    _expect(health.status_code == 200, f'/health returned {health.status_code}')
    health_json = _get_json(health)
    _expect(health_json.get('app') == 'ok', 'health payload missing app=ok')
    _print_step('health', f"mongodb={health_json.get('mongodb')} env={health_json.get('env')}")

    login_page = _request_with_retry(session, 'GET', f'{base_url}/login')
    _expect(login_page.status_code == 200, f'/login returned {login_page.status_code}')
    _print_step('login page', f'status={login_page.status_code}')

    login = _request_with_retry(
        session,
        'POST',
        f'{base_url}/login',
        data={'email': email, 'password': password},
        allow_redirects=False,
    )
    _expect(login.status_code in (302, 303), f'login failed with status {login.status_code}')
    _expect('/student/dashboard' in login.headers.get('Location', ''), 'login did not redirect to student dashboard')
    _print_step('login', f"redirect={login.headers.get('Location', '')}")

    wellness = _request_with_retry(session, 'GET', f'{base_url}/student/api/wellness/current')
    _expect(wellness.status_code == 200, f'/student/api/wellness/current returned {wellness.status_code}')
    wellness_json = _get_json(wellness)
    _expect('stress' in wellness_json and 'value' in wellness_json['stress'], 'wellness payload missing stress.value')
    _print_step('wellness api', f"stress={wellness_json['stress']['value']} label={wellness_json['stress'].get('label', '')}")

    dashboard = _request_with_retry(session, 'GET', f'{base_url}/student/api/student/dashboard-data')
    _expect(dashboard.status_code == 200, f'/student/api/student/dashboard-data returned {dashboard.status_code}')
    dashboard_json = _get_json(dashboard)
    _expect('mood' in dashboard_json and 'streak' in dashboard_json, 'dashboard payload missing mood/streak')
    _print_step('dashboard api', f"mood={dashboard_json.get('mood')} streak={dashboard_json.get('streak')}")

    if not skip_chat:
        chat_history = _request_with_retry(session, 'GET', f'{base_url}/api/chat/history')
        _expect(chat_history.status_code == 200, f'/api/chat/history returned {chat_history.status_code}')
        history_json = _get_json(chat_history)
        history_items = history_json.get('history') if isinstance(history_json, dict) else None
        _expect(isinstance(history_items, list), 'chat history payload missing history list')
        _print_step('chat history api', f'items={len(history_items)}')

    if live_chat:
        chat = _request_with_retry(
            session,
            'POST',
            f'{base_url}/api/chat/mental',
            json={
                'message': 'Hello AURA, this is a deployment smoke test. Please reply briefly.',
                'kind': 'mental',
                'context': [],
            },
        )
        _expect(chat.status_code == 200, f'/api/chat/mental returned {chat.status_code}')
        chat_json = _get_json(chat)
        _expect(bool(chat_json.get('ai_response')), 'chat response missing ai_response')
        _print_step('live chat api', f"stress_score={chat_json.get('stress_score')} sentiment={chat_json.get('sentiment')}")

    logout = _request_with_retry(session, 'GET', f'{base_url}/logout', allow_redirects=False)
    _expect(logout.status_code in (302, 303), f'/logout returned {logout.status_code}')
    _print_step('logout', f"redirect={logout.headers.get('Location', '')}")


def main() -> int:
    parser = argparse.ArgumentParser(description='Run AURA deployment smoke tests')
    parser.add_argument('--base-url', default=os.getenv('AURA_BASE_URL', 'http://127.0.0.1:5000'))
    parser.add_argument('--email', default=DEFAULT_EMAIL)
    parser.add_argument('--password', default=DEFAULT_PASSWORD)
    parser.add_argument('--skip-chat', action='store_true')
    parser.add_argument('--live-chat', action='store_true', help='Also exercise the AI-backed mental chat endpoint')
    args = parser.parse_args()

    try:
        run_smoke(args.base_url, args.email, args.password, skip_chat=args.skip_chat, live_chat=args.live_chat)
        print('[PASS] smoke test completed successfully')
        return 0
    except (requests.RequestException, SmokeFailure) as exc:
        print(f'[FAIL] {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
