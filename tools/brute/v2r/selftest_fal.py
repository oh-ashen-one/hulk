#!/usr/bin/env python3
# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
"""Self-tests for generate_fal.py that spend nothing.

    python3 -I tools/brute/v2r/selftest_fal.py mock <scenario> <generate_fal args...>
    python3 -I tools/brute/v2r/selftest_fal.py live

mock: generate_fal.py with its HTTP layer (call, download) replaced by fakes: no socket is opened, the key is a fake
set in the environment. Scenarios: ok, stop_waiting, fal_failed, balance403, low_balance, auth401, submit_neterr.
live: read-only calls with the real key (price, balance, status-URL shapes for a request id that does not exist);
submits nothing.
"""
import importlib.util
import os
import sys
from pathlib import Path

GF = Path(__file__).resolve().with_name('generate_fal.py')


def load():
    spec = importlib.util.spec_from_file_location('generate_fal', GF)
    gf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gf)
    return gf


def mock(scenario, argv):
    os.environ['FAL_KEY'] = 'fakeid:fakesecretvalue123456'
    gf = load()
    gf.POLL_S = gf.BACKOFF_S = 0
    gf.time.sleep = lambda s: None
    log, polls = [], {'n': 0}
    rid = 'req-0001'
    su = f'https://queue.fal.run/minimax/h3/requests/{rid}/status'
    ru = f'https://queue.fal.run/minimax/h3/requests/{rid}'
    locked = '{"detail":"User is locked. Reason: Exhausted balance. Top up your balance at fal.ai/dashboard/billing."}'

    def call(method, url, body=None, auth=True, timeout=120):
        log.append((method, url.split('?')[0]))
        if '/models/pricing' in url:
            return {'prices': [{'endpoint_id': gf.ENDPOINT, 'unit_price': 0.05, 'unit': 'seconds', 'currency': 'USD'}]}
        if '/account/billing' in url:
            bal = 0.10 if scenario == 'low_balance' else (23.40 if polls['n'] > 2 else 23.65)
            return {'username': 'x', 'credits': {'current_balance': bal, 'currency': 'USD'}}
        if '/billing-events' in url:
            return {'billing_events': [{'request_id': rid, 'cost_total': 0.25, 'unit_quantity': 5}]}
        if method == 'POST':
            assert body['resolution'] == '768P' and body['prompt_expansion_mode'] == 'disabled'
            assert body['image_url'].startswith('data:image/png;base64,') and body['sync_mode'] is False
            assert 'No visual effects of any kind' in body['prompt'] and isinstance(body['seed'], int)
            if scenario == 'balance403':
                raise gf.ApiError(f'POST: HTTP 403 {locked}', 403, locked)
            if scenario == 'auth401':
                b = '{"detail":"Invalid key fakeid:fakesecretvalue123456"}'
                raise gf.ApiError(f'POST: HTTP 401 {b}', 401, b)
            if scenario == 'submit_neterr':
                raise gf.Transient('POST: URLError timed out')
            return {'request_id': rid, 'status_url': su, 'response_url': ru, 'cancel_url': ru + '/cancel',
                    'queue_position': 0}
        if url.startswith(su):
            polls['n'] += 1
            if scenario == 'stop_waiting':
                raise gf.Transient('GET status: URLError network down')
            if scenario == 'fal_failed' and polls['n'] >= 2:
                return {'status': 'COMPLETED', 'request_id': rid, 'error': 'Generation failed: content policy',
                        'error_type': 'content_policy_violation'}
            st = ['IN_QUEUE', 'IN_PROGRESS', 'IN_PROGRESS', 'COMPLETED'][min(polls['n'] - 1, 3)]
            r = {'status': st, 'request_id': rid, 'logs': [{'message': f'step {polls["n"]}', 'timestamp': 't'}]}
            if st == 'IN_QUEUE':
                r['queue_position'] = 1
            if st == 'COMPLETED':
                r['metrics'] = {'inference_time': 61.2}
            return r
        if url == ru:
            return {'video': {'url': 'https://v3b.fal.media/files/x/clip.mp4', 'content_type': 'video/mp4',
                              'file_name': 'clip.mp4', 'file_size': 12}, 'expanded_prompt': None}
        raise AssertionError(f'unexpected {method} {url}')

    def download(url, path):
        log.append(('DOWNLOAD', url))
        path.write_bytes(b'FAKEMP4BYTES')

    gf.call, gf.download = call, download
    sys.argv = ['generate_fal.py'] + argv
    try:
        code = gf.main() or 0
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
    calls = [(m, 'cdn' if m == 'DOWNLOAD' else u.split('/')[-1]) for m, u in log]
    print(f'[selftest] scenario={scenario} exit={code} calls={calls}')
    return code


def live():
    gf = load()
    print('price  ->', gf.price_per_s(gf.ENDPOINT))
    print('balance->', gf.balance())
    bogus = '00000000-0000-0000-0000-000000000000'
    for base in (gf.owner_app(gf.ENDPOINT), gf.ENDPOINT):
        for tail in ('/status', ''):
            path = f'/{base}/requests/{bogus}{tail}'
            try:
                print('GET', path, '-> 200', str(gf.call('GET', gf.QUEUE + path, timeout=30))[:200])
            except (gf.ApiError, gf.Transient) as e:
                print('GET', path, '->', str(e).split(': ', 1)[-1][:200])
    return 0


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'live':
        sys.exit(live())
    if len(sys.argv) >= 3 and sys.argv[1] == 'mock':
        sys.exit(mock(sys.argv[2], sys.argv[3:]))
    sys.exit(__doc__)
