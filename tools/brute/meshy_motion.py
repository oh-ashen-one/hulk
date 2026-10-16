#!/usr/bin/env python3
# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Meshy motion pipeline for the Brute (owner, 2026-10-15: "use Tripo or Meshy, whichever is best"):
#   rig      <glb_url> [height]          -> Meshy auto-rig of the Customuse model (biped), prints rig task id
#   motion   "<prompt>" <seconds> [out.fbx] -> Text to Motion (prime, 10 credits), prints motion task id; optionally downloads the raw clip
#   motion-dl <motion_id> <out.fbx>       -> download a finished Text to Motion clip (free)
#   apply    <rig_id> <motion_id> <out>   -> retarget the motion onto the rigged Brute, download the animated GLB to <out>
#   library  [search] [category]          -> list the preset animation library (free)
#   apply-action <rig_id> <action_id> <out> -> apply a preset library action (3 credits), download the animated GLB
#   balance
# The key is read in-process from ~/.agents-md/.secrets/meshy.env (MESHY_API_KEY); it is never printed or passed on a command line.
import json, os, sys, time, urllib.request, urllib.error, urllib.parse

API = 'https://api.meshy.ai/openapi'

def key():
    if os.environ.get('MESHY_API_KEY'): return os.environ['MESHY_API_KEY']
    for line in open(os.path.expanduser('~/.agents-md/.secrets/meshy.env')):
        line = line.strip()
        if line.startswith('MESHY_API_KEY='): return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise SystemExit('MESHY_API_KEY missing')

def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Authorization': 'Bearer ' + key(), 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r: return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        raise SystemExit('Meshy %s %s -> %d %s' % (method, path, e.code, e.read()[:400].decode(errors='replace')))

def wait(path, label):
    t0 = time.time()
    while True:
        t = call('GET', path)
        st = t.get('status')
        if st in ('SUCCEEDED', 'FAILED', 'CANCELED', 'EXPIRED'):
            print('%s %s in %.0fs, credits %s' % (label, st, time.time() - t0, t.get('consumed_credits')), file=sys.stderr)
            if st != 'SUCCEEDED': raise SystemExit('%s failed: %s' % (label, t.get('task_error')))
            return t
        time.sleep(5)

def main():
    a = sys.argv[1:]
    if not a: raise SystemExit(__doc__)
    if a[0] == 'balance': print(call('GET', '/v1/balance')); return
    if a[0] == 'rig':
        src = a[1]
        if os.path.isfile(src):   # local GLB -> data URI (<= 100 MB)
            import base64
            src = 'data:application/octet-stream;base64,' + base64.b64encode(open(src, 'rb').read()).decode()
        tid = call('POST', '/v1/rigging', {'model_url': src, 'height_meters': float(a[2]) if len(a) > 2 else 2.6})['result']
        print('rig task', tid, file=sys.stderr); wait('/v1/rigging/' + tid, 'rig'); print(tid); return
    if a[0] == 'motion':
        tid = call('POST', '/v1/text-to-motion', {'prompt': a[1], 'duration': float(a[2]), 'mode': 'prime'})['result']
        print('motion task', tid, file=sys.stderr); t = wait('/v1/text-to-motion/' + tid, 'motion'); print(tid)
        if len(a) > 3:   # also download the raw motion clip (FBX, Meshy skeleton): retarget_motion.py reads it directly, no apply credits
            urllib.request.urlretrieve(t['result']['motion_url'], a[3]); print(a[3], os.path.getsize(a[3]), file=sys.stderr)
        return
    if a[0] == 'motion-dl':   # motion-dl <motion_id> <out.fbx>: re-download a finished Text to Motion clip (free, 3-day retention)
        t = call('GET', '/v1/text-to-motion/' + a[1]); urllib.request.urlretrieve(t['result']['motion_url'], a[2]); print(a[2]); return
    if a[0] == 'library':   # free: list preset actions, optional search / category filter
        q = []
        if len(a) > 1 and a[1]: q.append('search=' + urllib.parse.quote(a[1]))
        if len(a) > 2 and a[2]: q.append('category=' + urllib.parse.quote(a[2]))
        for x in call('GET', '/v1/animations/library' + ('?' + '&'.join(q) if q else '')):
            print('%4d  %-34s %-14s %s' % (x['action_id'], x['name'], x.get('category'), x.get('sub_category')))
        return
    if a[0] in ('apply', 'apply-action'):
        body = {'rig_task_id': a[1]}
        if a[0] == 'apply': body['motion_task_id'] = a[2]
        else: body['action_id'] = int(a[2])
        tid = call('POST', '/v1/animations', body)['result']
        print('animation task', tid, file=sys.stderr); t = wait('/v1/animations/' + tid, 'apply')
        r = t.get('result') or {}
        url = r.get('animation_glb_url') or r.get('animation_fbx_url')
        if not url: raise SystemExit('no animation url: %s' % list(r))
        urllib.request.urlretrieve(url, a[3]); print(a[3], os.path.getsize(a[3])); return
    raise SystemExit('unknown command ' + a[0])

if __name__ == '__main__':
    main()
