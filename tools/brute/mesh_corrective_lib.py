# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Shared definitions for the Brute corrective shape keys (mesh_corrective*.py). THE GAME MUST REPRODUCE elevation() + weights().
import math
import numpy as np

# arm elevation, degrees: angle between the upper-arm direction (Arm joint -> ForeArm joint) and the TORSO-down direction
# (Neck joint -> Spine1 joint). Joint = bone head position in any common space (world / component). 0 = arm hanging along the
# torso, 90 = horizontal (T-pose), 180 = straight overhead. Torso-relative, so leaning / crouching does not change it.
UP_A0, UP_A1 = 100.0, 150.0     # CorrArmUp_X   weight up   = smoothstep(UP_A0, UP_A1, elev)
SIDE_A0, SIDE_A1 = 50.0, 85.0   # CorrArmSide_X weight side = smoothstep(SIDE_A0, SIDE_A1, elev) * (1 - up)
USE_SIDE = True


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def elev_from_points(arm_p, fore_p, neck_p, spine1_p):
    a = np.asarray(fore_p, float) - np.asarray(arm_p, float)
    d = np.asarray(spine1_p, float) - np.asarray(neck_p, float)
    c = float(np.dot(a, d) / max(1e-12, np.linalg.norm(a) * np.linalg.norm(d)))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def elevation(arm, side):
    P = lambda n: np.array(arm.matrix_world @ arm.pose.bones[n].head)
    return elev_from_points(P(side + 'Arm'), P(side + 'ForeArm'), P('Neck'), P('Spine1'))


def weights_v1(arm):
    """v1 mapping (brute_rigged_corr_v1.glb): {shape key name: weight}"""
    out = {}
    for s in ('Left', 'Right'):
        e = elevation(arm, s); up = smoothstep(UP_A0, UP_A1, e)
        out['CorrArmUp_' + s[0]] = up
        if USE_SIDE: out['CorrArmSide_' + s[0]] = smoothstep(SIDE_A0, SIDE_A1, e) * (1 - up)
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# v2 (2026-10-18): direction-aware keys. Torso frame from joints only:
#   t   = normalize(Neck - Spine1)                         (torso up)
#   l   = LeftArm - RightArm, minus its t component, normalized   (towards the character's left)
#   f   = cross(t, l)  -- sign fixed so that f is the character's FORWARD (checked at bind: toes point along +f)
#   per side: o = l (Left) / -l (Right) = outward;  u = normalize(ForeArm - Arm)
#   elev = degrees(acos(clamp(-dot(u, t))))   (identical to v1 elev);  az = degrees(atan2(dot(u, f), dot(u, o)))
#          az 0 = arm out to the side, +90 = forward, -90 = backward
FWD_SIGN = -1.0  # probe at bind: cross(t, l) points backwards (toes . cross < 0) -> forward = -cross(t, l) = cross(l, t)


def torso_frame(P):
    t = P('Neck') - P('Spine1'); t = t / np.linalg.norm(t)
    l = P('LeftArm') - P('RightArm'); l = l - np.dot(l, t) * t; l = l / np.linalg.norm(l)
    f = FWD_SIGN * np.cross(t, l)
    return t, l, f


def arm_dir(P, side):
    """unit upper-arm direction in the torso frame: (outward, forward, up) components"""
    t, l, f = torso_frame(P)
    o = l if side == 'Left' else -l
    u = P(side + 'ForeArm') - P(side + 'Arm'); u = u / np.linalg.norm(u)
    return np.array([np.dot(u, o), np.dot(u, f), np.dot(u, t)])


def dir_from_angles(elev, az):
    e, a = math.radians(elev), math.radians(az)
    return np.array([math.sin(e) * math.cos(a), math.sin(e) * math.sin(a), -math.cos(e)])


def angles_from_dir(v):
    return math.degrees(math.acos(max(-1.0, min(1.0, -v[2])))), math.degrees(math.atan2(v[1], v[0]))


def posefn(arm):
    return lambda n: np.array(arm.matrix_world @ arm.pose.bones[n].head)


# v2 keys: normalised Gaussian RBF over the arm direction, gated by elevation (exactly 0 below 50 deg -> rest / Idle untouched)
#   theta_j = angle (deg) between u and centre j;  k_j = exp(-(theta_j / SIGMA)^2)
#   w_j     = gate(elev) * k_j / (sum over ALL centres incl. the null centres of k)      gate = smoothstep(50, 85, elev)
SCHEME = __import__('os').environ.get('CORR_SCHEME', 'v2')
SIGMA = 28.0
GATE = (50.0, 85.0)
CENTERS = [('CorrArmUp', 180.0, 0.0),        # straight overhead (azimuth irrelevant)            Uppercut top, Smash top
           ('CorrArmUpFwd', 135.0, 60.0),    # raised high, in front                             Lift hold, Throw, WallAttach
           ('CorrArmUpSide', 135.0, 0.0),    # raised high, out to the side                       Jump, Land
           ('CorrArmFwd', 90.0, 70.0),       # horizontal, forward                                punches, Clap close
           ('CorrArmSide', 85.0, 0.0),       # horizontal, out to the side                        Clap wide, Fall
           ('CorrArmMidFwd', 115.0, 65.0),   # between Fwd and UpFwd
           ('CorrArmLowFwd', 70.0, 50.0),    # low-forward (arm swings, lift start)
           ('CorrArmMidSide', 115.0, 0.0),   # between Side and UpSide
           ('CorrArmLowSide', 65.0, 10.0)]   # low-side
NULLS = [(90.0, -90.0)]                    # arm behind the body: no key (absorbs weight)
_os = __import__('os')
if _os.environ.get('CORR_CENTERS'):        # experiments: "Name:elev:az,..."
    CENTERS = [(n, float(e), float(a)) for n, e, a in (x.split(':') for x in _os.environ['CORR_CENTERS'].split(','))]
SIGMA = float(_os.environ.get('CORR_SIGMA', SIGMA))
CDIRS = [dir_from_angles(e, a) for _, e, a in CENTERS] + [dir_from_angles(e, a) for e, a in NULLS]


def key_names(side):
    s = side[0]
    if SCHEME == 'v1': return ['CorrArmUp_' + s, 'CorrArmSide_' + s]
    return [n + '_' + s for n, _, _ in CENTERS]


def weights_from_dir(v):
    elev, _ = angles_from_dir(v)
    th = np.degrees(np.arccos(np.clip(np.array([np.dot(v, c) for c in CDIRS]), -1, 1)))
    k = np.exp(-(th / SIGMA) ** 2)
    return smoothstep(GATE[0], GATE[1], elev) * k[:len(CENTERS)] / k.sum()


def weights(arm):
    """{shape key name: weight} for the current pose (THE GAME MAPPING)"""
    if SCHEME == 'v1': return weights_v1(arm)
    P = posefn(arm); out = {}
    for side in ('Left', 'Right'):
        for n, w in zip(key_names(side), weights_from_dir(arm_dir(P, side))): out[n] = float(w)
    return out
