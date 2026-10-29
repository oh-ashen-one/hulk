Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.

# tools/brute/v2r tests (2026-10-29, no spend)

Run on the Mac Studio M3 Ultra by the Phase 0 tooling engineer (Opus 5.5). Nothing was submitted to fal; no money
was spent. `$SCRATCH` = `/private/tmp/claude-501/-Users-midir/dc49ac78-9559-4631-aa7f-c07d9639c787/scratchpad`
(disposable). The dragon project `~/dragon-boss-fight/Local/video2rig/dragon` was only read.

## 1. generate_fal.py --dry-run (fake project, offline, no key needed)

Fake project: `$SCRATCH/fakeproj` = `creature.json`, `start/start.png` + `start/cameras.json` (copies of the
dragon's), `prompts/idle.txt`. Exit 0, nothing written (the `ls` shows no `clips/`).

```
$ env -u FAL_KEY python3 -I tools/brute/v2r/generate_fal.py $SCRATCH/fakeproj Idle_v2r_v1 --prompt $SCRATCH/fakeproj/prompts/idle.txt --dry-run --seed 1234
POST https://queue.fal.run/minimax/h3/image-to-video   (Authorization: Key <FAL_KEY from the environment or /Users/midir/.config/fal/secrets.env, not shown>)
{
 "prompt": "The green brute stands in both panels exactly as in the image, front view left, side view right. Static cameras, no zoom, no cuts. He breathes slowly and shifts his weight, then returns to the exact pose of the first frame. Keep the whole body inside the frame the whole time. No visual effects of any kind: no dust, no smoke, no debris, no sparks, no particles, no speed lines, no motion trails, no light trails, no motion blur, no camera shake. The blade and every limb stay sharp, the flat floor stays perfectly clean, and every foot, hand and held object stays clearly visible in every frame.",
 "image_url": "<data:image/png;base64, 2913512 base64 chars of $SCRATCH/fakeproj/start/start.png>",
 "resolution": "768P",
 "duration": 5,
 "prompt_expansion_mode": "disabled",
 "seed": 1234,
 "sync_mode": false
}
estimate: 0.05 USD/s x 5 s = 0.25 USD (price as of 2026-10-29; a real run reads it live); cap 2.0 USD; clip -> $SCRATCH/fakeproj/clips/Idle_v2r_v1.mp4
dry run: nothing sent
[exit 0]
```

## 2. generate_fal.py flow, offline (selftest_fal.py mock)

`selftest_fal.py mock` replaces generate_fal's two HTTP functions (`call`, `download`) with fakes: no socket is
opened, the key is a fake set in the environment. It asserts the request body (768P, prompt_expansion_mode
disabled, PNG data URI, integer seed, no-effects sentence present). Exit codes checked: 0 done, 2 other, 3 balance,
4 auth, 5 USD cap, 6 stopped while waiting (resume). The fake key never appears in output or in `clips/`
(`grep -rl fakesecretvalue` found nothing; the 401 body is printed as `<FAL_KEY>`).

```

$ python3 -I tools/brute/v2r/selftest_fal.py mock ok $SCRATCH/fakeproj Idle_v2r_v1 --prompt $SCRATCH/fakeproj/prompts/idle.txt
estimate 0.25 USD (0.05 USD/s x 5 s, 768P); cap 2.00 USD; balance 23.65 USD
Idle_v2r_v1: accepted, request req-0001 (saved in $SCRATCH/fakeproj/clips/Idle_v2r_v1.task.json)
  fal log: step 1
Idle_v2r_v1: IN_QUEUE (queue position 1) after 0 s
Idle_v2r_v1: IN_PROGRESS after 0 s
Idle_v2r_v1: COMPLETED after 0 s
Idle_v2r_v1: home -> $SCRATCH/fakeproj/clips/Idle_v2r_v1.mp4 (12 bytes) after 0 s; cost 0.25 USD billed, balance delta 0.25, estimate 0.25
[selftest] scenario=ok exit=0 calls=[('GET', 'pricing'), ('GET', 'billing'), ('POST', 'image-to-video'), ('GET', 'status'), ('GET', 'status'), ('GET', 'status'), ('GET', 'status'), ('GET', 'req-0001'), ('DOWNLOAD', 'cdn'), ('GET', 'billing'), ('GET', 'billing-events')]
[exit 0]

$ ls $SCRATCH/fakeproj/clips
Idle_v2r_v1.json
Idle_v2r_v1.mp4
Idle_v2r_v1.prompt.txt
[exit 0]

$ python3 -I tools/brute/v2r/selftest_fal.py mock ok $SCRATCH/fakeproj Idle_v2r_v1 --prompt $SCRATCH/fakeproj/prompts/idle.txt
$SCRATCH/fakeproj/clips/Idle_v2r_v1.mp4 exists: pick another clip name (bump the _vN suffix)
[selftest] scenario=ok exit=2 calls=[]
[exit 2]

$ python3 -I tools/brute/v2r/selftest_fal.py mock stop_waiting $SCRATCH/fakeproj Walk_v2r_v1 --prompt $SCRATCH/fakeproj/prompts/idle.txt
estimate 0.25 USD (0.05 USD/s x 5 s, 768P); cap 2.00 USD; balance 23.65 USD
Walk_v2r_v1: accepted, request req-0001 (saved in $SCRATCH/fakeproj/clips/Walk_v2r_v1.task.json)
Walk_v2r_v1: GET status: URLError network down; trying again in 0 s (1 of 7)
Walk_v2r_v1: GET status: URLError network down; trying again in 0 s (2 of 7)
Walk_v2r_v1: GET status: URLError network down; trying again in 0 s (3 of 7)
Walk_v2r_v1: GET status: URLError network down; trying again in 0 s (4 of 7)
Walk_v2r_v1: GET status: URLError network down; trying again in 0 s (5 of 7)
Walk_v2r_v1: GET status: URLError network down; trying again in 0 s (6 of 7)
Walk_v2r_v1: GET status: URLError network down; trying again in 0 s (7 of 7)
Walk_v2r_v1: 8 errors in a row, the last: GET status: URLError network down
The paid request goes on at fal. Bring it home later (no new charge) with:
  python3 /Users/midir/hulk/tools/brute/v2r/generate_fal.py $SCRATCH/fakeproj Walk_v2r_v1 --resume
[selftest] scenario=stop_waiting exit=6 calls=[('GET', 'pricing'), ('GET', 'billing'), ('POST', 'image-to-video'), ('GET', 'status'), ('GET', 'status'), ('GET', 'status'), ('GET', 'status'), ('GET', 'status'), ('GET', 'status'), ('GET', 'status'), ('GET', 'status')]
[exit 6]

$ python3 -I tools/brute/v2r/selftest_fal.py mock ok $SCRATCH/fakeproj Walk_v2r_v1 --prompt $SCRATCH/fakeproj/prompts/idle.txt
$SCRATCH/fakeproj/clips/Walk_v2r_v1.task.json holds a paid request that is not home yet: add --resume (never paid twice)
[selftest] scenario=ok exit=2 calls=[]
[exit 2]

$ python3 -I tools/brute/v2r/selftest_fal.py mock ok $SCRATCH/fakeproj Walk_v2r_v1 --resume
Walk_v2r_v1: resuming request req-0001
  fal log: step 1
Walk_v2r_v1: IN_QUEUE (queue position 1) after 1 s
Walk_v2r_v1: IN_PROGRESS after 1 s
Walk_v2r_v1: COMPLETED after 1 s
Walk_v2r_v1: home -> $SCRATCH/fakeproj/clips/Walk_v2r_v1.mp4 (12 bytes) after 1 s; cost 0.25 USD billed, balance delta 0.25, estimate 0.25
[selftest] scenario=ok exit=0 calls=[('GET', 'status'), ('GET', 'status'), ('GET', 'status'), ('GET', 'status'), ('GET', 'req-0001'), ('DOWNLOAD', 'cdn'), ('GET', 'billing'), ('GET', 'billing-events')]
[exit 0]

$ python3 -I tools/brute/v2r/selftest_fal.py mock balance403 $SCRATCH/fakeproj Run_v2r_v1 --prompt $SCRATCH/fakeproj/prompts/idle.txt
estimate 0.25 USD (0.05 USD/s x 5 s, 768P); cap 2.00 USD; balance 23.65 USD
Run_v2r_v1 submit: fal balance exhausted or billing refused (switch provider per PLAN.md): POST: HTTP 403 {"detail":"User is locked. Reason: Exhausted balance. Top up your balance at fal.ai/dashboard/billing."}
[selftest] scenario=balance403 exit=3 calls=[('GET', 'pricing'), ('GET', 'billing'), ('POST', 'image-to-video')]
[exit 3]

$ python3 -I tools/brute/v2r/selftest_fal.py mock low_balance $SCRATCH/fakeproj Run_v2r_v1 --prompt $SCRATCH/fakeproj/prompts/idle.txt
estimate 0.25 USD (0.05 USD/s x 5 s, 768P); cap 2.00 USD; balance 0.1 USD
REFUSED: fal balance 0.1 is below the estimate 0.25 USD: switch provider (Higgsfield MiniMax H3 Max per PLAN.md)
[selftest] scenario=low_balance exit=3 calls=[('GET', 'pricing'), ('GET', 'billing')]
[exit 3]

$ python3 -I tools/brute/v2r/selftest_fal.py mock auth401 $SCRATCH/fakeproj Run_v2r_v1 --prompt $SCRATCH/fakeproj/prompts/idle.txt
estimate 0.25 USD (0.05 USD/s x 5 s, 768P); cap 2.00 USD; balance 23.65 USD
Run_v2r_v1 submit: fal refused the key (HTTP 401): POST: HTTP 401 {"detail":"Invalid key <FAL_KEY>"}
[selftest] scenario=auth401 exit=4 calls=[('GET', 'pricing'), ('GET', 'billing'), ('POST', 'image-to-video')]
[exit 4]

$ env V2R_FAL_MAX_USD=0.20 python3 -I tools/brute/v2r/selftest_fal.py mock ok $SCRATCH/fakeproj Run_v2r_v1 --prompt $SCRATCH/fakeproj/prompts/idle.txt
estimate 0.25 USD (0.05 USD/s x 5 s, 768P); cap 0.20 USD; balance 23.65 USD
REFUSED: estimate 0.25 USD is over the per-clip cap 0.20 USD (V2R_FAL_MAX_USD)
[selftest] scenario=ok exit=5 calls=[('GET', 'pricing'), ('GET', 'billing')]
[exit 5]

$ python3 -I tools/brute/v2r/selftest_fal.py mock fal_failed $SCRATCH/fakeproj Smash_v2r_v1 --prompt $SCRATCH/fakeproj/prompts/idle.txt
estimate 0.25 USD (0.05 USD/s x 5 s, 768P); cap 2.00 USD; balance 23.65 USD
Smash_v2r_v1: accepted, request req-0001 (saved in $SCRATCH/fakeproj/clips/Smash_v2r_v1.task.json)
  fal log: step 1
Smash_v2r_v1: IN_QUEUE (queue position 1) after 0 s
Smash_v2r_v1: COMPLETED after 0 s
Smash_v2r_v1: fal reports failure: Generation failed: content policy (details in $SCRATCH/fakeproj/clips/Smash_v2r_v1.failed.json)
[selftest] scenario=fal_failed exit=2 calls=[('GET', 'pricing'), ('GET', 'billing'), ('POST', 'image-to-video'), ('GET', 'status'), ('GET', 'status')]
[exit 2]

$ python3 -I tools/brute/v2r/selftest_fal.py mock submit_neterr $SCRATCH/fakeproj Clap_v2r_v1 --prompt $SCRATCH/fakeproj/prompts/idle.txt
estimate 0.25 USD (0.05 USD/s x 5 s, 768P); cap 2.00 USD; balance 23.65 USD
Clap_v2r_v1 submit: POST: URLError timed out
The request may have been accepted all the same: look at https://fal.ai/dashboard/requests (or GET https://api.fal.ai/v1/models/requests/by-endpoint?endpoint_id=minimax/h3/image-to-video) before trying again; if it is there, write its id to $SCRATCH/fakeproj/clips/Clap_v2r_v1.task.json as {"request_id": "<id>", "endpoint": "minimax/h3/image-to-video"} and run --resume.
[selftest] scenario=submit_neterr exit=2 calls=[('GET', 'pricing'), ('GET', 'billing'), ('POST', 'image-to-video')]
[exit 2]

$ ls $SCRATCH/fakeproj/clips
Idle_v2r_v1.json
Idle_v2r_v1.mp4
Idle_v2r_v1.prompt.txt
Smash_v2r_v1.failed.json
Smash_v2r_v1.prompt.txt
Walk_v2r_v1.json
Walk_v2r_v1.mp4
Walk_v2r_v1.prompt.txt
```

What this shows: the task file is written on acceptance and survives a stopped wait (exit 6); a second paid run is
refused while it exists (exit 2, no HTTP call); `--resume` brings the clip home with no POST; an existing mp4 is
never overwritten; fal's 403 "Exhausted balance" body and a known balance below the estimate both exit 3; 401 exits
4; the cap (V2R_FAL_MAX_USD) exits 5 before any POST; a fal-side failure writes `clips/<clip>.failed.json` and
removes the task file; a lost answer to the POST is never retried (it may hide a paid request).

Provenance written by the mock run (`clips/Idle_v2r_v1.json`, prompt omitted; cost numbers are the fakes):
provider fal, model/endpoint, request_id, start + sha256, resolution 768P, duration 5, seed + seed_source,
prompt_expansion_mode, expanded_prompt, submitted/completed/seconds_to_ready, metrics.inference_time, video
url/content_type/file_name/file_size, status_url/response_url, cost {price, estimate_usd, balance_before,
balance_after, balance_delta_usd, billing_event, cost_total_usd}.

## 3. Live read-only checks with the real key (nothing submitted)

```
$ python3 -I tools/brute/v2r/selftest_fal.py live

$ python3 -I tools/brute/v2r/selftest_fal.py live
price  -> {'endpoint_id': 'minimax/h3/image-to-video', 'unit_price': 0.05, 'unit': 'seconds', 'currency': 'USD'}
balance-> {'current_balance': 23.65, 'currency': 'USD'}
GET /minimax/h3/requests/00000000-0000-0000-0000-000000000000/status -> HTTP 404 {"status":"NOT_FOUND"}
GET /minimax/h3/requests/00000000-0000-0000-0000-000000000000 -> HTTP 404 {"detail":"Request not found"}
GET /minimax/h3/image-to-video/requests/00000000-0000-0000-0000-000000000000/status -> HTTP 405 
GET /minimax/h3/image-to-video/requests/00000000-0000-0000-0000-000000000000 -> HTTP 405 
[exit 0]
```

- Status/result URLs: the owner/app form `queue.fal.run/minimax/h3/requests/<id>[/status]` is the live route (404
  for an unknown id = route exists); the full-path form the endpoint's OpenAPI lists answers **405**. This matches
  fal's queue docs, not the OpenAPI. generate_fal.py uses the URLs fal returns on submit, and for a hand-made task
  file tries owner/app first, then the full path.
- `GET https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=minimax/h3/image-to-video` (no key): **HTTP 200,
  7314 bytes**. Input schema confirmed: prompt (required, max 50000 chars), image_url, end_image_url, resolution
  enum 480P/768P/2K/4K (**schema default 2K**: we always send 768P), duration int **5..15** (default 5),
  prompt_expansion_mode (default balanced; we send disabled), seed, enable_safety_checker (default true, not sent),
  sync_mode, target_audio_url. Output: video {url, content_type, file_name, file_size}, expanded_prompt. No price,
  pricing or cost field anywhere in the spec.
- Pricing fields reachable without a job:
  - `GET https://api.fal.ai/v1/models?q=minimax` (key): 200, 72 endpoints, fields endpoint_id + metadata
    (category, date, description, display_name, duration_estimate, group, ..., updated_at). **No pricing field.**
  - `GET https://api.fal.ai/v1/models/pricing?endpoint_id=minimax/h3/image-to-video` (key): **200,
    {"unit_price": 0.05, "unit": "seconds", "currency": "USD"}** = 0.25 USD for a 5 s clip at the base rate. fal
    says the price may be adjusted proportionally for resolution/length; the real charge per clip comes from the
    billing feed below.
  - `GET https://api.fal.ai/v1/account/billing?expand=credits` (key): **200, current_balance 23.65 USD**.
  - `GET https://api.fal.ai/v1/models/billing-events?request_id=...` (key): 200 (no events yet on this account
    this week). generate_fal.py reads the clip's cost_total from here after each run (with retries, since the feed
    can lag) and also records the balance before/after.

## 4. size_gate.py on the dragon's real clips (read-only)

Command (per clip, both metrics), run under the fork's venv:

```
~/video2rig/.venv/bin/python tools/brute/v2r/size_gate.py ~/dragon-boss-fight/Local/video2rig/dragon <clip> \
    [--metric box] --json $SCRATCH/gate/<clip>.<metric>.json --debug-dir $SCRATCH/gate/dbg
```

Box width/height = max over panels of the silhouette box vs frame 0 (3-frame running median); scale = sqrt of the
silhouette area vs frame 0 (max over panels). Limit 1.30; edge rule: FAIL if a panel edge is touched for 12+ frames.

| clip | generator | box width | box height | scale | verdict, metric area (default) | verdict, metric box |
| --- | --- | --- | --- | --- | --- | --- |
| idle | minimax_h3_max | 1.02 | 1.10 | 1.05 | **PASS** | **PASS** |
| idle_look | seedance_2_5 | 1.00 | 1.00 | 1.00 | **PASS** | **PASS** |
| bite | seedance_2_5 | 1.14 | 1.15 | 1.12 | **PASS** | **PASS** |
| claw_swipe | seedance_2_5 | 1.09 | 1.21 | 1.18 | **PASS** | **PASS** |
| stagger | seedance_2_5 | 1.13 | 1.00 | 1.07 | **PASS** | **PASS** |
| rise | seedance_2_5 | 1.16 | 1.38 | 1.18 | **PASS** | **FAIL** (rears onto hind legs) |
| land2 | seedance_2_5 | 1.06 | 1.57 | 1.19 | **PASS** | **FAIL** (hop pitches the body up) |
| collapse | seedance_2_5 | 1.09 | 1.02 | 1.06 | **PASS** | **PASS** |
| death | seedance_2_5 | 1.07 | 1.01 | 1.01 | **PASS** | **PASS** |
| roar | minimax_h3_max | 1.20 | 2.30 | 1.55 | **FAIL** | **FAIL** |
| roar2 | minimax_h3_max | 1.20 | 2.29 | 1.56 | **FAIL** | **FAIL** |
| roar_sd | seedance_2_5 | 1.23 | 1.35 | 1.24 | **FAIL** (wings off both front edges 60+ frames) | **FAIL** |
| roar_sd2 | seedance_2_5 | 1.10 | 1.30 | 1.17 | **PASS** | **PASS** |
| land | seedance_2_5 | 1.22 | 1.74 | 1.26 | **FAIL** (edges 14-16 frames) | **FAIL** |
| takeoff | seedance_2_5 | 1.23 | 2.02 | 1.39 | **FAIL** | **FAIL** |
| takeoff2 | seedance_2_5 | 1.23 | 1.96 | 1.31 | **FAIL** | **FAIL** |

Against the expectation: every clip whose refined notes give raw wing peaks of 1.00-1.24x (bite, claw_swipe,
stagger, rise, land2; plus idle, collapse, death) PASSES with the default metric; both MiniMax roars that drew the
wings at about 2x FAIL with either metric (scale 1.55 / 1.56, front wings off both panel edges for 64 / 80+
frames). land, takeoff and takeoff2 (which also failed video2rig's check) FAIL. With the literal box metric, rise
and land2 also FAIL, on pose, not size; that is why area is the default and box is kept as `--metric box`.
Front-panel box width saturates at about 1.20-1.23 when wings leave the panel (the box cannot grow past the edge),
which is why the edge rule exists.

Full output, MiniMax roar (default metric):

```
SIZE_GATE roar FAIL width 1.20 height 2.30 peak_frame 68 scale 1.55 metric area
  limit 1.30 on scale = sqrt(silhouette area / frame 0) per panel; edge rule 12 frames; panels: split line found at x 418-419 of 960 (cameras.json: 420)
  v2r_front: width 1.20 (raw 1.20) at frame 37 | height 1.93 (raw 1.93) at frame 66 | scale 1.26 at frame 59 | frame-0 box 342x210 px of 418x549 | frame0/start w 1.02 h 1.003
  v2r_side: width 1.02 (raw 1.02) at frame 30 | height 2.30 (raw 2.30) at frame 64 | scale 1.55 at frame 68 | frame-0 box 432x210 px of 540x549 | frame0/start w 1.017 h 1.003
  lateral reach at peak frame 68 (vs frame 0, from the frame-0 box centre): v2r_front L 1.19 R 1.22, v2r_side L 1.02 R 0.89
  worst: v2r_side scale 1.55 at frame 68 of 124; limit 1.30
  FAIL: v2r_side scale ratio 1.55 > 1.30 at frame 68
  FAIL: v2r_front: silhouette touches the left edge of the panel in 64 frames (first 37, last 100); frame 0 did not: the part leaves the panel, its size cannot be measured there
  FAIL: v2r_front: silhouette touches the right edge of the panel in 64 frames (first 37, last 100); frame 0 did not: the part leaves the panel, its size cannot be measured there
  WARN: v2r_side: silhouette touches the top edge of the panel in 10 frames (first 64, last 73); frame 0 did not (under 12 frames: brief contact, look at the clip)
exit 1
```

Bite (Seedance omni-reference clip: the generator moved the split line to the midline, x 479 of 960, where
cameras.json says 420; the line is found in the clip itself; the head touches the split line for 4 frames = WARN):

```
SIZE_GATE bite PASS width 1.14 height 1.15 peak_frame 32 scale 1.12 metric area
  limit 1.30 on scale = sqrt(silhouette area / frame 0) per panel; edge rule 12 frames; panels: split line found at x 479-480 of 960 (cameras.json: 420)
  v2r_front: width 1.11 (raw 1.12) at frame 28 | height 1.12 (raw 1.13) at frame 34 | scale 1.12 at frame 32 | frame-0 box 392x234 px of 479x540 | frame0/start w 1.021 h 1.136
  v2r_side: width 1.14 (raw 1.14) at frame 40 | height 1.15 (raw 1.15) at frame 34 | scale 1.07 at frame 39 | frame-0 box 414x233 px of 479x540 | frame0/start w 1.099 h 1.131
  lateral reach at peak frame 32 (vs frame 0, from the frame-0 box centre): v2r_front L 1.12 R 1.11, v2r_side L 0.67 R 1.00
  worst: v2r_front scale 1.12 at frame 32 of 121; limit 1.30
  WARN: v2r_side: silhouette touches the left edge of the panel in 4 frames (first 40, last 43); frame 0 did not (under 12 frames: brief contact, look at the clip)
  WARN: v2r_front: frame 0 differs from the start picture by 14% in box size: the generator reframed the start, or the start picture is not this clip's
  WARN: v2r_side: frame 0 differs from the start picture by 13% in box size: the generator reframed the start, or the start picture is not this clip's
exit 0
```

Rise with `--metric box` (the pose false positive):

```
SIZE_GATE rise FAIL width 1.16 height 1.38 peak_frame 97 scale 1.18 metric box
  limit 1.30 on box width and height / frame 0 per panel; edge rule 12 frames; panels: split line found at x 430-431 of 960 (cameras.json: 420)
  v2r_front: width 1.16 (raw 1.16) at frame 98 | height 1.34 (raw 1.34) at frame 82 | scale 1.18 at frame 97 | frame-0 box 345x205 px of 430x540 | frame0/start w 1.001 h 0.995
  v2r_side: width 1.05 (raw 1.06) at frame 40 | height 1.38 (raw 1.38) at frame 97 | scale 1.11 at frame 92 | frame-0 box 431x203 px of 528x540 | frame0/start w 1.038 h 0.985
  lateral reach at peak frame 97 (vs frame 0, from the frame-0 box centre): v2r_front L 1.20 R 1.12, v2r_side L 0.64 R 0.81
  worst: v2r_side height 1.38 at frame 97 of 121; limit 1.30
  FAIL: v2r_side height ratio 1.38 > 1.30 at frame 97
  FAIL: v2r_front height ratio 1.34 > 1.30 at frame 82
  WARN: v2r_front: silhouette touches the left edge of the panel in 10 frames (first 98, last 107); frame 0 did not (under 12 frames: brief contact, look at the clip)
exit 1
```

Debug overlays (silhouette tinted, frame-0 box green, peak box red) were checked by eye for roar peak 68, bite frame
0, land2 peak 48 and rise frame 102: the silhouettes cover the dragon, wings included, and no backdrop.
Files: `$SCRATCH/gate/dbg/*.png` (disposable). Runtime about 7-10 s per 5 s clip.

## Known limits

- Reference = the clip's frame 0. Seedance omni-reference clips re-framed the start picture by 13-38% in box size
  (WARN lines); the ratios stay valid because both sides of each ratio come from the same clip.
- The Brute is a humanoid: a punch toward the side camera or a clap with arms spread can double a box width
  without changing the body's size, so `--metric box` would fail most attacks. The area metric is tolerant of
  that, but it would also miss limbs drawn too long. A rig-reach reference (a start-style render of the rig at its
  widest legal reach) as the denominator would close that gap; not built here.
