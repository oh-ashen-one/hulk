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


def weights(arm):
    """{shape key name: weight} for the current pose"""
    out = {}
    for s in ('Left', 'Right'):
        e = elevation(arm, s); up = smoothstep(UP_A0, UP_A1, e)
        out['CorrArmUp_' + s[0]] = up
        if USE_SIDE: out['CorrArmSide_' + s[0]] = smoothstep(SIDE_A0, SIDE_A1, e) * (1 - up)
    return out
