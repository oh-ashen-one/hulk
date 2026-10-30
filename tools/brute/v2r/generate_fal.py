#!/usr/bin/env python3
# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
"""MiniMax H3 image-to-video on fal.ai (queue API) for a video2rig project: the project's start picture goes in as
the first frame, the prompt from a text file, and the clip lands where video2rig reads it.

    python3 tools/brute/v2r/generate_fal.py <project_dir> <clip> --prompt <file> [--duration 5] [--resolution 768P]
        [--seed N] [--end] [--start path] [--image-url URL] [--expansion disabled] [--dry-run] [--resume]

Plain python3, stdlib only (no fal_client). Same contract as the fork's video2rig/generate.py (BytePlus):
  clips/<clip>.mp4          the video (audio kept), downloaded to .part first and renamed when complete
  clips/<clip>.json         provenance: provider 'fal', endpoint, resolution, duration, seed, prompt, request_id,
                            timestamps, price/balance/billing fields fal exposes (null where it does not)
  clips/<clip>.prompt.txt   the prompt exactly as sent (no-effects sentence appended)
  clips/<clip>.task.json    written the moment fal accepts the request (request_id + the status/response URLs fal
                            returned); a new paid run of the same clip refuses while it exists; --resume brings the
                            clip home without paying again; deleted once the clip is home (or fal reports failure)

Key: FAL_KEY from the environment, else the line FAL_KEY=... in ~/.config/fal/secrets.env, read in-process. It is
never printed, logged, written or put on a command line; error bodies are scrubbed of it before printing.

Queue API (fal docs 2026-10-29, https://fal.ai/docs/model-endpoints/queue):
  POST https://queue.fal.run/<endpoint>          -> {request_id, status_url, response_url, cancel_url, queue_position}
  GET  <status_url>?logs=1                       -> {status: IN_QUEUE | IN_PROGRESS | COMPLETED, logs, metrics,
                                                     error, error_type (failed requests)}
  GET  <response_url>                            -> {video: {url, content_type, file_name, file_size}, expanded_prompt}
  The docs say status/result URLs of a sub-path endpoint use only owner/app (queue.fal.run/minimax/h3/requests/<id>),
  while the endpoint's OpenAPI lists the full path: the URLs fal returns are used, and a hand-made task file falls
  back to owner/app first, then the full path.
Price and balance (read-only platform API, same key): GET https://api.fal.ai/v1/models/pricing?endpoint_id=...
(unit_price per second, 0.05 USD on 2026-10-29), GET https://api.fal.ai/v1/account/billing?expand=credits
(current_balance), GET https://api.fal.ai/v1/models/billing-events?request_id=... (cost_total after the run).

Spend guard: the estimate (unit_price x seconds) is refused over $V2R_FAL_MAX_USD (default 2.00 per clip), and when the
account balance is known and below the estimate. One clip per run, never fanned out.

--provider seedance2 (2026-10-30): ByteDance Seedance 2.0 image-to-video on the same queue protocol,
  endpoint bytedance/seedance-2.0/image-to-video (fal OpenAPI 2026-10-30: required prompt, image_url; duration string
  'auto'|'4'..'15'; resolution 480p|720p|1080p|4k; aspect_ratio; generate_audio; codec auto|H264|H265; bitrate_mode
  standard|high; end_image_url; no seed input, the seed used comes back in the result). Body sent: prompt, image_url,
  duration "<n>", resolution (default 720p), aspect_ratio (default 16:9), generate_audio true (Higgsfield refused 4 of
  5 audio-off takes of this model), codec H264, bitrate_mode standard [, end_image_url with --end]. Fallback price
  0.1547 USD/s at 720p (2026-10-30). After download, a clip that is not 1280x720 H.264 at a constant 24 fps is kept as
  clips/<clip>.orig.mp4 and re-encoded with ffmpeg to clips/<clip>.mp4 (1280x720, H.264, CFR 24, audio AAC); the
  .json records both probes. The default provider stays minimax, unchanged.

Exit codes: 0 done (or dry run) | 2 other failure | 3 balance exhausted (switch provider) | 4 auth failure (401/403)
| 5 refused by the per-clip USD cap | 6 stopped while waiting: the paid request goes on at fal, run --resume.
"""
import argparse
import base64
import datetime as dt
import hashlib
import http.client
import json
import os
import random
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = 'minimax/h3/image-to-video'
QUEUE = 'https://queue.fal.run'
PLATFORM = 'https://api.fal.ai/v1'
SECRETS = Path.home() / '.config' / 'fal' / 'secrets.env'
RESOLUTIONS = ('480P', '768P', '2K', '4K')
FALLBACK_USD_PER_S = 0.05            # GET /v1/models/pricing for minimax/h3/image-to-video, 2026-10-29
DEFAULT_CAP_USD = 2.00

SD2_ENDPOINT = 'bytedance/seedance-2.0/image-to-video'
SD2_RESOLUTIONS = ('480p', '720p', '1080p', '4k')
SD2_FALLBACK_USD_PER_S = 0.1547      # 720p, owner brief 2026-10-30 (a real run reads GET /v1/models/pricing live)
SD2_ASPECTS = ('auto', '21:9', '16:9', '4:3', '1:1', '3:4', '9:16')
TARGET_W, TARGET_H, TARGET_FPS = 1280, 720, 24   # what video2rig reads; seedance2 clips are normalised to this

POLL_S = 10
BACKOFF_S, BACKOFF_MAX_S = 15, 300
MAX_FAILS = 8                        # errors in a row while waiting before the run stops (resume later)

EXIT_OTHER, EXIT_BALANCE, EXIT_AUTH, EXIT_CAP, EXIT_STOPPED = 2, 3, 4, 5, 6

# Upstream's wording (~/video2rig/docs/VIDEO.md "No effects, ever" = video2rig/generate.py NO_EFFECTS), adapted for the Brute
# (no blade, no held object: a thrown or lifted load is never drawn) plus the two sentences of ~/video2rig/TUTORIAL.md step 7
# (fast shutter, divider line).
NO_EFFECTS = ('Shot at a very fast shutter speed: no motion blur at all, every frame is sharp. '
              'No visual effects of any kind: no dust, no smoke, no debris, no sparks, no particles, no speed lines, '
              'no motion trails, no light trails, no motion blur, no camera shake. Both fists, both arms, both bare feet '
              'and the torn shorts stay sharp, nothing is drawn that is not in the first frame (no object, no weapon, '
              'no second figure), the flat floor stays perfectly clean, the thin dark divider line stays in place, '
              'and every hand and foot stays clearly visible in every frame.')

BALANCE_WORDS = ('balance', 'credit', 'exhausted', 'top up', 'top-up', 'insufficient', 'payment required',
                 'billing', 'funds', 'quota')


class Fail(SystemExit):
    """A clear message on stderr and a meaningful exit code."""

    def __init__(self, msg, code=EXIT_OTHER):
        print(scrub(msg), file=sys.stderr, flush=True)
        super().__init__(code)


class Transient(Exception):
    """Worth trying again: the network, a timeout, HTTP 429 or 5xx."""


class ApiError(Exception):
    def __init__(self, msg, status=None, body=''):
        super().__init__(msg)
        self.status, self.body = status, body


# --- key, never shown -----------------------------------------------------------------------------------------
_KEY = None


def load_key():
    """The key or '' (never raises, never prints)."""
    k = os.environ.get('FAL_KEY', '').strip()
    if not k and SECRETS.exists():
        for line in SECRETS.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith('export '):
                line = line[7:].strip()
            if line.startswith('FAL_KEY='):
                k = line.split('=', 1)[1].strip().strip('"').strip("'")
    return k


def key():
    global _KEY
    if not _KEY:
        _KEY = load_key() or None
        if not _KEY:
            raise Fail(f'no fal key: set FAL_KEY or put a FAL_KEY=... line in {SECRETS}', EXIT_AUTH)
    return _KEY


def scrub(text):
    text = str(text)
    global _KEY
    if not _KEY:
        _KEY = load_key() or None            # loaded quietly so it can be scrubbed from anything printed
    if _KEY:
        text = text.replace(_KEY, '<FAL_KEY>')
        if ':' in _KEY:
            for part in _KEY.split(':'):
                if len(part) >= 8:
                    text = text.replace(part, '<FAL_KEY>')
    return text


def is_balance(text):
    t = str(text).lower()
    return any(w in t for w in BALANCE_WORDS)


# --- HTTP ---------------------------------------------------------------------------------------------------------
def call(method, url, body=None, auth=True, timeout=120):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    headers = {'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    if auth:
        headers['Authorization'] = f'Key {key()}'
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode('utf-8')
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        txt = scrub(e.read().decode('utf-8', 'replace')[:1500])
        msg = f'{method} {url}: HTTP {e.code} {txt}'
        if e.code == 429 or e.code >= 500:
            raise Transient(msg) from e
        raise ApiError(msg, e.code, txt) from e
    except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, http.client.HTTPException,
            json.JSONDecodeError) as e:
        raise Transient(f'{method} {url}: {type(e).__name__} {scrub(e)}') from e


def classify(e, where):
    """An ApiError -> the matching exit."""
    if isinstance(e, ApiError):
        if e.status == 402 or is_balance(e.body):
            raise Fail(f'{where}: fal balance exhausted or billing refused (switch provider per PLAN.md): {e}',
                       EXIT_BALANCE)
        if e.status in (401, 403):
            raise Fail(f'{where}: fal refused the key (HTTP {e.status}): {e}', EXIT_AUTH)
    raise Fail(f'{where}: {e}', EXIT_OTHER)


def with_retries(fn, what, tries=MAX_FAILS):
    fails = 0
    while True:
        try:
            return fn()
        except Transient as e:
            fails += 1
            if fails >= tries:
                raise
            pause = min(BACKOFF_S * 2 ** (fails - 1), BACKOFF_MAX_S)
            print(f'{what}: {e}; trying again in {pause} s ({fails} of {tries - 1})', flush=True)
            time.sleep(pause)


def download(url, path):
    """The clip to a .part file first, renamed when complete: a broken download never looks like a clip. The CDN URL
    is public: no key is sent there."""
    part = path.with_name(path.name + '.part')
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'video2rig-generate-fal'})
        with urllib.request.urlopen(req, timeout=300) as r, open(part, 'wb') as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
    except urllib.error.HTTPError as e:
        part.unlink(missing_ok=True)
        if e.code == 429 or e.code >= 500:
            raise Transient(f'download {path.name}: HTTP {e.code}') from e
        raise ApiError(f'download {path.name}: HTTP {e.code}', e.code) from e
    except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, http.client.HTTPException) as e:
        part.unlink(missing_ok=True)
        raise Transient(f'download {path.name}: {type(e).__name__} {e}') from e
    if part.stat().st_size == 0:
        part.unlink(missing_ok=True)
        raise Transient(f'download {path.name}: empty file')
    part.replace(path)


# --- platform API (read-only, never fatal) ------------------------------------------------------------------------
def price_per_s(endpoint):
    try:
        r = call('GET', f'{PLATFORM}/models/pricing?endpoint_id={urllib.parse.quote(endpoint, safe="/")}', timeout=30)
        for p in r.get('prices', []):
            if p.get('endpoint_id') == endpoint:
                return p
    except (Transient, ApiError) as e:
        print(f'price lookup failed ({e}); using {FALLBACK_USD_PER_S} USD/s from 2026-10-29', flush=True)
    return None


def balance():
    try:
        r = call('GET', f'{PLATFORM}/account/billing?expand=credits', timeout=30)
        c = r.get('credits') or {}
        if c.get('current_balance') is not None:
            return {'current_balance': c['current_balance'], 'currency': c.get('currency')}
    except (Transient, ApiError) as e:
        print(f'balance lookup failed ({e})', flush=True)
    return None


def billing_event(request_id, since, tries=4, pause=20):
    """The request's billed cost; fal's billing feed can lag, so a few looks, then None."""
    for i in range(tries):
        try:
            q = urllib.parse.urlencode({'request_id': request_id, 'start': since, 'limit': 10})
            r = call('GET', f'{PLATFORM}/models/billing-events?{q}', timeout=30)
            ev = [e for e in r.get('billing_events', []) if e.get('request_id') == request_id]
            if ev:
                return ev[0]
        except (Transient, ApiError) as e:
            print(f'billing-event lookup failed ({e})', flush=True)
            return None
        if i < tries - 1:
            time.sleep(pause)
    return None


# --- project, prompt, request ---------------------------------------------------------------------------------
def start_dir(project):
    cfg = project / 'creature.json'
    if cfg.exists():
        try:
            return project / json.loads(cfg.read_text(encoding='utf-8')).get('start', 'start')
        except json.JSONDecodeError:
            pass
    return project / 'start'


def with_no_effects(prompt):
    return prompt if 'no visual effects' in prompt.lower() else prompt.rstrip() + ' ' + NO_EFFECTS


def data_uri(path):
    mime = 'image/png' if path.suffix.lower() == '.png' else 'image/jpeg'
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode('ascii')


def build_body(a, prompt, start, seed):
    if getattr(a, 'provider', 'minimax') == 'seedance2':
        return build_body_sd2(a, prompt, start)
    img = a.image_url if a.image_url else data_uri(start)
    body = {'prompt': prompt, 'image_url': img, 'resolution': a.resolution, 'duration': a.duration,
            'prompt_expansion_mode': a.expansion, 'seed': seed, 'sync_mode': False}
    if a.end:
        body['end_image_url'] = img
    return body


def build_body_sd2(a, prompt, start):
    """Seedance 2.0 i2v body (fal schema): no seed and no prompt expansion inputs exist for this model."""
    img = a.image_url if a.image_url else data_uri(start)
    body = {'prompt': prompt, 'image_url': img, 'duration': str(a.duration), 'resolution': a.resolution,
            'aspect_ratio': a.aspect_ratio, 'generate_audio': not a.no_audio, 'codec': 'H264',
            'bitrate_mode': 'standard'}
    if a.end:
        body['end_image_url'] = img
    return body


def _ffbin(name):
    import shutil
    return shutil.which(name) or f'/opt/homebrew/bin/{name}'


def probe(mp4):
    """ffprobe of the first video stream: {codec, width, height, r_frame_rate, avg_frame_rate, nb_frames, duration}."""
    import subprocess
    out = subprocess.run([_ffbin('ffprobe'), '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                          'stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames:format=duration',
                          '-of', 'json', str(mp4)], capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f'ffprobe {mp4.name}: {out.stderr.strip()[:300]}')
    d = json.loads(out.stdout)
    st = (d.get('streams') or [{}])[0]
    return {'codec': st.get('codec_name'), 'width': st.get('width'), 'height': st.get('height'),
            'r_frame_rate': st.get('r_frame_rate'), 'avg_frame_rate': st.get('avg_frame_rate'),
            'nb_frames': int(st['nb_frames']) if str(st.get('nb_frames', '')).isdigit() else None,
            'duration': float((d.get('format') or {}).get('duration') or 0) or None}


def conforms(pr):
    from fractions import Fraction

    def fr(x):
        try:
            return Fraction(x)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    return (pr.get('codec') == 'h264' and pr.get('width') == TARGET_W and pr.get('height') == TARGET_H
            and fr(pr.get('r_frame_rate')) == TARGET_FPS and fr(pr.get('avg_frame_rate')) == TARGET_FPS)


def normalise(clips, clip, mp4):
    """seedance2 only: a clip that is not 1280x720 H.264 CFR 24 becomes <clip>.orig.mp4 and an ffmpeg re-encode takes
    its place as <clip>.mp4. Never fatal (the clip is paid for): a failure leaves the download as <clip>.mp4."""
    import subprocess
    rec = {'target': f'{TARGET_W}x{TARGET_H} h264 cfr {TARGET_FPS}', 'reencoded': False}
    try:
        rec['downloaded'] = probe(mp4)
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as e:
        rec['error'] = scrub(e)
        print(f'{clip}: probe failed ({e}); clip left as downloaded', flush=True)
        return rec
    if conforms(rec['downloaded']):
        rec['final'] = rec['downloaded']
        return rec
    orig = clips / f'{clip}.orig.mp4'
    tmp = clips / f'{clip}.norm.tmp.mp4'
    cmd = [_ffbin('ffmpeg'), '-v', 'error', '-y', '-i', str(mp4), '-map', '0:v:0', '-map', '0:a?',
           '-vf', f'scale={TARGET_W}:{TARGET_H}:flags=lanczos,fps={TARGET_FPS},format=yuv420p',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-r', str(TARGET_FPS), '-fps_mode', 'cfr',
           '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(tmp)]
    rec['ffmpeg'] = ' '.join(['ffmpeg'] + cmd[1:]).replace(str(clips) + '/', '')
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip()[:400])
        fin = probe(tmp)
        if not conforms(fin):
            raise RuntimeError(f're-encode does not conform: {fin}')
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as e:
        tmp.unlink(missing_ok=True)
        rec['error'] = scrub(e)
        print(f'{clip}: re-encode failed ({e}); clip left as downloaded', flush=True)
        return rec
    mp4.replace(orig)
    tmp.replace(mp4)
    rec.update(reencoded=True, original=orig.name, final=fin)
    print(f'{clip}: re-encoded to {TARGET_W}x{TARGET_H} H.264 CFR {TARGET_FPS} (original kept as {orig.name})',
          flush=True)
    return rec


def redacted(body, start):
    out = dict(body)
    for k in ('image_url', 'end_image_url'):
        v = out.get(k)
        if isinstance(v, str) and v.startswith('data:'):
            out[k] = f'<{v[:v.index(",")]}, {len(v) - v.index(",") - 1} base64 chars of {start}>'
    return out


def owner_app(endpoint):
    return '/'.join(endpoint.split('/')[:2])


def status_urls(job):
    """Where to ask: the URLs fal returned; else owner/app (fal docs), then the full endpoint path (OpenAPI)."""
    rid, ep = job['request_id'], job.get('endpoint', ENDPOINT)
    if job.get('status_url') and job.get('response_url'):
        return [(job['status_url'], job['response_url'])]
    return [(f'{QUEUE}/{base}/requests/{rid}/status', f'{QUEUE}/{base}/requests/{rid}')
            for base in (owner_app(ep), ep)]


def with_logs(url):
    return url + ('&' if '?' in url else '?') + 'logs=1'


def job_write(path, job):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes(json.dumps(job, indent=1).encode('utf-8'))
    tmp.replace(path)


def now_iso():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# --- waiting ------------------------------------------------------------------------------------------------------
def wait(clips, clip, path, job, resume_hint, timeout_min):
    t_end = time.time() + timeout_min * 60
    urls = status_urls(job)
    fails, last_state, last_log = 0, None, 0
    while True:
        if time.time() > t_end:
            raise Fail(f'{clip}: still not done after {timeout_min} min (last status {last_state}).\n{resume_hint}',
                       EXIT_STOPPED)
        try:
            st = None
            for i, (su, ru) in enumerate(urls):
                try:
                    st = call('GET', with_logs(su))
                    if len(urls) > 1:                       # found the shape that works: keep it
                        urls = [(su, ru)]
                        job['status_url'], job['response_url'] = su, ru
                        job_write(path, job)
                    break
                except ApiError as e:
                    if e.status in (404, 405) and i < len(urls) - 1:
                        continue
                    raise
        except Transient as e:
            fails += 1
            if fails >= MAX_FAILS:
                raise Fail(f'{clip}: {MAX_FAILS} errors in a row, the last: {e}\n{resume_hint}', EXIT_STOPPED)
            pause = min(BACKOFF_S * 2 ** (fails - 1), BACKOFF_MAX_S)
            print(f'{clip}: {e}; trying again in {pause} s ({fails} of {MAX_FAILS - 1})', flush=True)
            time.sleep(pause)
            continue
        except ApiError as e:
            if e.status in (401, 403) and not is_balance(e.body):
                raise Fail(f'{clip}: status refused (HTTP {e.status}): {e}\n{resume_hint}', EXIT_AUTH)
            classify(e, f'{clip} status')
        fails = 0
        state = st.get('status')
        logs = st.get('logs') or []
        if isinstance(logs, list) and len(logs) > last_log:
            for lg in logs[last_log:]:
                print(f'  fal log: {scrub(lg.get("message", lg) if isinstance(lg, dict) else lg)}', flush=True)
            last_log = len(logs)
        if state != last_state:
            extra = f' (queue position {st.get("queue_position")})' if state == 'IN_QUEUE' else ''
            print(f'{clip}: {state}{extra} after {round(time.time() - job["submitted_s"])} s', flush=True)
            last_state = state
        if state == 'COMPLETED':
            return st, urls[0][1]
        time.sleep(POLL_S)


def finish(clips, clip, path, job, st, response_url, resume_hint):
    err = st.get('error') or st.get('error_type')
    result = None
    if not err:
        try:
            result = with_retries(lambda: call('GET', response_url), f'{clip} result')
        except Transient as e:
            raise Fail(f'{clip}: result not fetched: {e}\n{resume_hint}', EXIT_STOPPED)
        except ApiError as e:
            err = f'result HTTP {e.status}: {e.body}'
            result = None
    if err or not (result or {}).get('video', {}).get('url'):
        why = err or f'no video in the result: {json.dumps(result)[:800]}'
        fail = {**{k: v for k, v in job.items()}, 'failed': now_iso(), 'error': scrub(why),
                'error_type': st.get('error_type'), 'status': st}
        (clips / f'{clip}.failed.json').write_bytes(json.dumps(fail, indent=1).encode('utf-8'))
        path.unlink(missing_ok=True)                 # fal ended it: nothing left to bring home
        code = EXIT_BALANCE if is_balance(why) else EXIT_OTHER
        raise Fail(f'{clip}: fal reports failure: {why} (details in {clips / clip}.failed.json)', code)
    video = result['video']
    mp4 = clips / f'{clip}.mp4'
    try:
        with_retries(lambda: download(video['url'], mp4), f'{clip} download')
    except (Transient, ApiError) as e:
        raise Fail(f'{clip}: download failed: {e}\n{resume_hint}', EXIT_STOPPED)
    sd2 = job.get('provider') == 'seedance2'
    norm = normalise(clips, clip, mp4) if sd2 else None
    done_s = time.time()
    bal_after = balance()
    ev = billing_event(job['request_id'], job.get('submitted_day') or job['submitted'][:10] + 'T00:00:00Z')
    bal_before = (job.get('balance_before') or {}).get('current_balance')
    meta = {
        'provider': 'fal', 'model': job['endpoint'], 'endpoint': job['endpoint'], 'task': job['request_id'],
        'request_id': job['request_id'], 'start': job['start'], 'start_sha256': job.get('start_sha256'),
        'image_source': job.get('image_source'), 'end_frame': job.get('end_frame', False),
        'prompt': job['prompt'], 'prompt_expansion_mode': job['body'].get('prompt_expansion_mode'),
        'expanded_prompt': result.get('expanded_prompt'),
        'resolution': job['body']['resolution'], 'duration': job['body']['duration'], 'duration_s': job['body']['duration'],
        'seed': job['body'].get('seed'), 'seed_source': job.get('seed_source'),
        'enable_safety_checker': 'fal default (not sent)', 'sync_mode': False,
        'submitted': job['submitted'], 'completed': now_iso(), 'seconds_to_ready': round(done_s - job['submitted_s']),
        'metrics': st.get('metrics'), 'video': {k: video.get(k) for k in ('url', 'content_type', 'file_name', 'file_size')},
        'bytes_on_disk': mp4.stat().st_size,
        'status_url': job.get('status_url'), 'response_url': response_url,
        'cost': {
            'price': job.get('price'), 'estimate_usd': job.get('estimate_usd'),
            'balance_before': job.get('balance_before'), 'balance_after': bal_after,
            'balance_delta_usd': (round(bal_before - bal_after['current_balance'], 4)
                                  if bal_before is not None and bal_after else None),
            'billing_event': ev, 'cost_total_usd': (ev or {}).get('cost_total'),
            'note': None if ev else 'fal billing feed had no event for this request yet: read it later with GET '
                                    f'{PLATFORM}/models/billing-events?request_id={job["request_id"]}',
        },
    }
    if sd2:
        b = job['body']
        meta['provider_option'] = 'seedance2'
        meta['params'] = {k: b.get(k) for k in ('duration', 'resolution', 'aspect_ratio', 'generate_audio', 'codec',
                                                 'bitrate_mode') if k in b}
        meta['params']['end_image_url'] = 'start picture' if 'end_image_url' in b else None
        meta['duration_s'] = int(b['duration']) if str(b.get('duration', '')).isdigit() else b.get('duration')
        meta['seed'] = result.get('seed')
        meta['seed_source'] = 'returned by fal (seedance2 has no seed input)'
        meta['enable_safety_checker'] = 'not an input of this endpoint'
        meta['normalised'] = norm
        meta['bytes_on_disk'] = mp4.stat().st_size
        orig = clips / f'{clip}.orig.mp4'
        meta['bytes_on_disk_orig'] = orig.stat().st_size if (norm or {}).get('reencoded') else None
    (clips / f'{clip}.json').write_bytes(json.dumps(meta, indent=1).encode('utf-8'))
    path.unlink(missing_ok=True)
    c = meta['cost']
    print(f'{clip}: home -> {mp4} ({meta["bytes_on_disk"]} bytes) after {meta["seconds_to_ready"]} s; cost '
          f'{c["cost_total_usd"]} USD billed, balance delta {c["balance_delta_usd"]}, estimate {c["estimate_usd"]}',
          flush=True)


# --- main ---------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(prog='generate_fal.py', description=__doc__.split('\n\n')[0])
    ap.add_argument('project')
    ap.add_argument('clip')
    ap.add_argument('--prompt', help='a text file with the prompt (required unless --resume)')
    ap.add_argument('--duration', type=int, default=5, help='seconds, 5..15 (fal schema), default 5')
    ap.add_argument('--provider', default='minimax', choices=('minimax', 'seedance2'),
                    help=f'minimax (default: {ENDPOINT}) | seedance2 ({SD2_ENDPOINT})')
    ap.add_argument('--resolution', default=None, help=f'minimax: {"|".join(RESOLUTIONS)} (default 768P); '
                    f'seedance2: {"|".join(SD2_RESOLUTIONS)} (default 720p)')
    ap.add_argument('--aspect-ratio', default='16:9', choices=SD2_ASPECTS, help='seedance2 only (default 16:9)')
    ap.add_argument('--no-audio', action='store_true', help='seedance2 only: generate_audio false (default true)')
    ap.add_argument('--seed', type=int, default=None, help='default: a random seed chosen here and recorded')
    ap.add_argument('--end', action='store_true', help='loops: also send the start picture as end_image_url')
    ap.add_argument('--start', help='first frame (default <project>/start/start.png)')
    ap.add_argument('--image-url', help='send this URL as image_url instead of the start picture as a data URI')
    ap.add_argument('--expansion', default='disabled', help="prompt_expansion_mode: disabled (default, literal "
                    "prompt) | fast | balanced | quality")
    ap.add_argument('--endpoint', default=None, help='default: the provider\'s endpoint')
    ap.add_argument('--timeout-min', type=float, default=60.0, help='stop waiting after this (resume later)')
    ap.add_argument('--dry-run', action='store_true', help='print the request (no image bytes, no key) and exit')
    ap.add_argument('--resume', action='store_true', help='no new request: bring home the one in clips/<clip>.task.json')
    a = ap.parse_args()
    sd2 = a.provider == 'seedance2'
    res_ok = SD2_RESOLUTIONS if sd2 else RESOLUTIONS
    if a.resolution is None:
        a.resolution = '720p' if sd2 else '768P'
    elif a.resolution not in res_ok:
        ap.error(f"argument --resolution: invalid choice: '{a.resolution}' (choose from "
                 f"{', '.join(repr(r) for r in res_ok)})")
    if a.endpoint is None:
        a.endpoint = SD2_ENDPOINT if sd2 else ENDPOINT

    project = Path(a.project).expanduser().resolve()
    if not project.is_dir():
        raise Fail(f'project folder not found: {project}')
    clips = project / 'clips'
    path = clips / f'{a.clip}.task.json'
    script = Path(__file__).resolve()
    resume_hint = (f'The paid request goes on at fal. Bring it home later (no new charge) with:\n'
                   f'  python3 {script} {a.project} {a.clip} --resume')

    if a.resume:
        if not path.exists():
            raise Fail(f'{path} not found: no unfinished request for {a.clip}')
        job = json.loads(path.read_text(encoding='utf-8'))
        if not job.get('request_id'):
            raise Fail(f'{path} has no request_id')
        job.setdefault('endpoint', ENDPOINT)
        job.setdefault('submitted_s', round(time.time()))
        job.setdefault('submitted', now_iso())
        job.setdefault('prompt', '')
        job.setdefault('start', None)
        job.setdefault('body', {'prompt_expansion_mode': None, 'resolution': None, 'duration': None, 'seed': None})
        if (clips / f'{a.clip}.mp4').exists():
            raise Fail(f'{clips / a.clip}.mp4 is already here; delete {path} by hand if it is the finished clip')
        print(f'{a.clip}: resuming request {job["request_id"]}', flush=True)
    else:
        if not a.prompt:
            ap.error('--prompt is required (unless --resume)')
        if sd2:
            if not 4 <= a.duration <= 15:
                ap.error(f'--duration must be 4..15 s (fal schema for {SD2_ENDPOINT})')
        elif not 5 <= a.duration <= 15:
            ap.error('--duration must be 5..15 s (fal schema for minimax/h3/image-to-video)')
        if path.exists():
            raise Fail(f'{path} holds a paid request that is not home yet: add --resume (never paid twice)')
        if (clips / f'{a.clip}.mp4').exists():
            raise Fail(f'{clips / a.clip}.mp4 exists: pick another clip name (bump the _vN suffix)')
        start = Path(a.start).expanduser().resolve() if a.start else start_dir(project) / 'start.png'
        if not a.image_url and not start.exists():
            raise Fail(f'start picture not found: {start}')
        prompt = with_no_effects(Path(a.prompt).read_text(encoding='utf-8').strip())
        seed, seed_source = (a.seed, 'given') if a.seed is not None else (random.randrange(1, 2 ** 31 - 1), 'random, chosen here')
        if sd2:
            if a.seed is not None:
                print('note: seedance2 has no seed input; --seed is ignored (fal returns the seed it used)', flush=True)
            seed, seed_source = None, 'not sent (seedance2 has no seed input)'
        elif a.aspect_ratio != '16:9' or a.no_audio:
            ap.error('--aspect-ratio / --no-audio apply to --provider seedance2 only')
        body = build_body(a, prompt, start, seed)
        unit = SD2_FALLBACK_USD_PER_S if sd2 else FALLBACK_USD_PER_S
        price_day = '2026-10-30' if sd2 else '2026-10-29'
        if a.dry_run:
            print(f'POST {QUEUE}/{a.endpoint}   (Authorization: Key <FAL_KEY from the environment or {SECRETS}, '
                  f'not shown>)')
            print(json.dumps(redacted(body, start), indent=1))
            if sd2:
                print('seed: not an input of seedance2 (fal returns the seed it used; recorded in the .json)')
            elif seed_source != 'given':
                print('seed: chosen at random for this printout; a real run picks its own and records it (--seed N '
                      'to fix it)')
            print(f'estimate: {unit} USD/s x {a.duration} s = {unit * a.duration:.2f} USD (price as of {price_day}; a '
                  f'real run reads it live); cap {os.environ.get("V2R_FAL_MAX_USD", DEFAULT_CAP_USD)} USD; '
                  f'clip -> {clips / a.clip}.mp4')
            print('dry run: nothing sent')
            return 0
        clips.mkdir(exist_ok=True)
        cap = float(os.environ.get('V2R_FAL_MAX_USD', DEFAULT_CAP_USD))
        price = price_per_s(a.endpoint)
        if price and price.get('unit') in ('seconds', 'second', 's'):
            unit = float(price['unit_price'])
        est = round(unit * a.duration, 4)
        if a.resolution in ('2K', '4K'):
            print(f'note: {a.resolution} upscales a 768P base; fal may charge more than the per-second base', flush=True)
        bal = balance()
        print(f'estimate {est:.2f} USD ({unit} USD/s x {a.duration} s, {a.resolution}); cap {cap:.2f} USD; balance '
              f'{bal["current_balance"] if bal else "unknown"} {bal.get("currency", "") if bal else ""}', flush=True)
        if est > cap:
            raise Fail(f'REFUSED: estimate {est:.2f} USD is over the per-clip cap {cap:.2f} USD (V2R_FAL_MAX_USD)', EXIT_CAP)
        if bal and float(bal['current_balance']) < est:
            raise Fail(f'REFUSED: fal balance {bal["current_balance"]} is below the estimate {est:.2f} USD: switch '
                       f'provider (Higgsfield MiniMax H3 Max per PLAN.md)', EXIT_BALANCE)
        t0 = time.time()
        r = None
        # Submit: only HTTP 429 is retried (a lost answer to a POST may hide an accepted, paid request).
        attempt = 0
        while r is None:
            attempt += 1
            try:
                r = call('POST', f'{QUEUE}/{a.endpoint}', body, timeout=180)
            except Transient as e:
                if 'HTTP 429' in str(e) and attempt < 4:
                    pause = BACKOFF_S * 2 ** (attempt - 1)
                    print(f'{a.clip} submit: rate limited; trying again in {pause} s', flush=True)
                    time.sleep(pause)
                    continue
                raise Fail(f'{a.clip} submit: {e}\nThe request may have been accepted all the same: look at '
                           f'https://fal.ai/dashboard/requests (or GET {PLATFORM}/models/requests/by-endpoint?'
                           f'endpoint_id={a.endpoint}) before trying again; if it is there, write its id to {path} as '
                           '{"request_id": "<id>", "endpoint": "' + a.endpoint + '"} and run --resume.', EXIT_OTHER)
            except ApiError as e:
                classify(e, f'{a.clip} submit')
        rid = r.get('request_id')
        if not rid:
            raise Fail(f'{a.clip} submit: no request_id in the answer: {json.dumps(r)[:600]}')
        job = {'request_id': rid, 'endpoint': a.endpoint, 'status_url': r.get('status_url'),
               'response_url': r.get('response_url'), 'cancel_url': r.get('cancel_url'),
               'queue_position': r.get('queue_position'), 'submitted': now_iso(), 'submitted_s': round(t0),
               'submitted_day': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT00:00:00Z'),
               'start': str(start) if not a.image_url else None,
               'start_sha256': hashlib.sha256(start.read_bytes()).hexdigest() if not a.image_url else None,
               'image_source': 'url' if a.image_url else 'data_uri', 'end_frame': bool(a.end),
               'prompt': prompt, 'body': redacted(body, start), 'seed_source': seed_source,
               'price': price, 'estimate_usd': est, 'balance_before': bal}
        if sd2:
            job['provider'] = 'seedance2'
        job_write(path, job)                                    # the moment fal has it
        (clips / f'{a.clip}.prompt.txt').write_text(prompt + '\n', encoding='utf-8')
        print(f'{a.clip}: accepted, request {rid} (saved in {path})', flush=True)

    st, response_url = wait(clips, a.clip, path, job, resume_hint, a.timeout_min)
    finish(clips, a.clip, path, job, st, response_url, resume_hint)
    if a.resume and job.get('prompt') and not (clips / f'{a.clip}.prompt.txt').exists():
        (clips / f'{a.clip}.prompt.txt').write_text(job['prompt'] + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
