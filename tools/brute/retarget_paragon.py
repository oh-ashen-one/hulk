"""Retarget the 17 Hulk (Brute) clips onto a free Paragon character (Fab, Epic Games).

Run headless inside the WebHomage project, picking the skin with BRUTE_SKIN (default Rampage):
  BRUTE_SKIN=Crunch UnrealEditor-Cmd WebHomage.uproject -run=pythonscript -script=tools/brute/retarget_paragon.py

Skins: Rampage = "Paragon: Rampage" Elemental (rock) skin; Crunch = "Paragon: Crunch" base mesh.
Needs the pack under /Game/Paragon<Hero> (Epic, Unreal-only licence;
never commit it to this public repo - Content/ is git-ignored, snapshots go to the private
webhomage-unreal-content repo).  Writes only new assets under /Game/Brute/<Skin>; the original
/Game/Brute/Body clips and SK_Brute are untouched.
"""
import os
import unreal

SKINS = {
    "Rampage": "/Game/ParagonRampage/Characters/Heroes/Rampage/Skins/Tier2/Elemental/Meshes/Rampage_Elemental",
    "Crunch": "/Game/ParagonCrunch/Characters/Heroes/Crunch/Meshes/Crunch",
}
SKIN = os.environ.get("BRUTE_SKIN", "Rampage")
SRC_MESH = "/Game/Brute/Body/SK_Brute"
TGT_MESH = SKINS[SKIN]
OUT = f"/Game/Brute/{SKIN}"
CLIPS = ["Clap", "Fall", "Idle", "Jump", "Land", "Lift", "PunchL", "PunchR", "Run", "Slap", "Smash",
         "StopLunge", "Throw", "Uppercut", "Walk", "WallAttach", "WallClimb"]

log = lambda m: unreal.log_warning(f"[paragon:{SKIN}] " + m)
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary


def make(name, cls, factory):
    path = f"{OUT}/{name}"
    if eal.does_asset_exist(path):   # re-run: reuse (clips reference it, so a delete can fail) and rebuild its contents
        return unreal.load_asset(path)
    return tools.create_asset(name, OUT, cls, factory)


src = unreal.load_asset(SRC_MESH)
tgt = unreal.load_asset(TGT_MESH)
assert src and tgt, f"missing mesh src={src} tgt={tgt}"
log(f"target skeleton: {tgt.skeleton.get_path_name()}")

rigs = {}
for key, mesh in (("Brute", src), (SKIN, tgt)):
    rig = make(f"IK_{key}", unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(mesh)
    ok_def = c.apply_auto_generated_retarget_definition()
    ok_ik = c.apply_auto_fbik()
    chains = [str(ch.chain_name) for ch in c.get_retarget_chains()]
    log(f"IK_{key}: auto-def={ok_def} fbik={ok_ik} root={c.get_retarget_root()} chains={chains}")
    rigs[key] = rig

S, T = unreal.RetargetSourceOrTarget.SOURCE, unreal.RetargetSourceOrTarget.TARGET
rtg = make(f"RTG_Brute_to_{SKIN}", unreal.IKRetargeter, unreal.IKRetargetFactory())
rc = unreal.IKRetargeterController.get_controller(rtg)
rc.set_ik_rig(S, rigs["Brute"])
rc.set_ik_rig(T, rigs[SKIN])
rc.set_preview_mesh(S, src)
rc.set_preview_mesh(T, tgt)
rc.remove_all_ops()
rc.add_default_ops()
rc.assign_ik_rig_to_all_ops(S, rigs["Brute"])
rc.assign_ik_rig_to_all_ops(T, rigs[SKIN])
# FK only: SK_Brute's bones carry a ~110x scale (Blender export), which throws the IK goals ~80 m off and makes the
# full-body IK op drag the whole body there; FK chains alone give the right pose. No root motion either: the game
# moves and places the body itself (BuildClipRig measures facing and foot height from an idle frame).
for i in reversed(range(rc.get_num_retarget_ops())):
    n = str(rc.get_op_name(i))
    if "Root Motion" in n:
        rc.remove_retarget_op(i)
    elif "IK Rig" in n:
        rc.set_retarget_op_enabled(i, False)
log("ops: " + str([(str(rc.get_op_name(i)), rc.get_retarget_op_enabled(i)) for i in range(rc.get_num_retarget_ops())]))
rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
rc.auto_align_all_bones(T)
eal.save_loaded_asset(rtg)

inputs = unreal.IKRetargetBatchOperationInputs()
inputs.assets_to_retarget = [unreal.EditorAssetLibrary.find_asset_data(f"/Game/Brute/Body/A_Brute_{c}") for c in CLIPS]
inputs.source_mesh = src
inputs.target_mesh = tgt
inputs.ik_retarget_asset = rtg
inputs.target_path = OUT
inputs.include_referenced_assets = False
inputs.overwrite_existing_files = True
out = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
log(f"retargeted {len(out)} assets: {[str(a.asset_name) for a in out]}")
for a in out:
    eal.save_asset(str(a.package_name), only_if_is_dirty=False)
for k in rigs:
    eal.save_loaded_asset(rigs[k])
log("DONE")
