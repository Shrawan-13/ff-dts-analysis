# FF DTS Analysis — Saved Workspace

This directory is the persistent hand-off for the Free Fire MAX 2.133.1
client-side headshot cheat analysis.

Start with:

1. `STATE.md` — full state, findings, evidence, next steps.
2. `reports/report-draft.md` — draft report with ranked vectors and mitigations.
3. `outputs/` — saved dumps and searches.
4. `scripts/dump_type_resolved.py` — main tool for metadata + ELF type resolution.

## Quick start

```bash
cd /home/shrawan/experiments/hackathon/analysis

# Recreate the Python environment if /tmp was cleared:
python3 -m venv /tmp/opencode/unityenv
/tmp/opencode/unityenv/bin/pip install pyelftools
source /tmp/opencode/unityenv/bin/activate

# Dump a type (fields with resolved types, methods with return type + param count):
python3 scripts/dump_type_resolved.py 32128

# Filter by member-name regex:
python3 scripts/dump_type_resolved.py '32128:aim|assist|head|hit|damage'
```

`FF_META` and `FF_BIN` override the default paths:

```bash
FF_META=/path/to/global-metadata.dec.dat \
FF_BIN=/path/to/libil2cpp.so \
python3 scripts/dump_type_resolved.py 438
```

Default paths:

- metadata: `analysis/data/global-metadata.dec.dat`
- binary: `extracted/work/config/lib/arm64-v8a/libil2cpp.so`

## Directory layout

```
analysis/
  STATE.md
  README.md
  scripts/
    dump_type_resolved.py
    mdparse.py
    findmembers.py
    dump_type.py
    literals.py
    disasm.py
    decrypt_metadata.py
  data/
    global-metadata.dec.dat
    assembly-csharp-patch.enc.bin
  outputs/
    player_aim_resolved.txt      Player fields/methods matching aim/hit/etc.
    player_sigs.txt              exact Player method signatures
    key1.txt                     BigHeadData, BodyPartUtilByName,
                                 HitDetectColliderHelper, auto-absorb data
    key2.txt                     WeaponGunFeelProfileData, UGC attachment/aim
                                 assist, custom hitbox, integrity validator
    key3.txt                     SettingDetail, GameModeSetting
    key4.txt                     GameVarDef, PlayerAttributes, UGCAimAssistEntity
    damage_types.txt             HNLIMBLIANL, PIAEKELILCJ, BEADLMGGGGL,
                                 LastAimingInfo
    collidertype_enum.txt        EHGMCNBHNMD values
    aim_types.txt                aim-assist classes
    aim_target_types.txt         OGKFEMJNCGM and target info
    hit_types.txt                hit detection, big head, UGC hitboxes
    ifix_types.txt               iFix patch loader
    bodypart_refs.txt            body-part/headshot field references
    net_payload_fields.txt       message payload keyword search
    net_fire_types.txt           fire/hit/damage message types
    lit_relevant.txt             relevant string literals/config keys
    members_aim*.txt             earlier aim-assist member searches
    player_aim.txt               earlier Player aim search
    members_hit.txt              hit/bodypart member search
    members_bone.txt             bone/hitbox member search
  reports/
    report-draft.md
  gh-repo-reference/
    analyze.py, analyze.yml, README.md
```

## Resume checklist

- [ ] Confirm the in-match payload carrying `EHITBODYPART`/`EHGMCNBHNMD`.
- [ ] Trace `set_LockedAimingCollider` and `SetAimRotation` callers.
- [ ] Test whether `BigHeadComponent.UpdateScale` affects enemy hit colliders.
- [ ] Inspect iFix for signature/hash verification and patch-load call sites.
- [ ] Confirm whether `extra_hitbox_*` and `DebugWeaponAimAssist*` are active.
- [ ] Fix the GitHub Actions workflow to be metadata-only.
- [ ] Finalize and push the report (do not commit game binaries or the 55 MB
      decrypted metadata).

## GitHub

Repo: `https://github.com/Shrawan-13/ff-dts-analysis`

Analysis state/report/scripts were pushed on 2026-10-28 in commit `8c8dfcc`
under `analysis/`. The 55 MB decrypted metadata and the encrypted patch bundle
are not committed.

The release tag `input` already contains the 427 MB XAPK. The current workflow
is dumper-dependent and fails; replace the Il2CppDumper step with a
metadata-only run. Token: retrieve from keyring with
`secret-tool lookup service gh:github.com username Shrawan-13`; never print or
persist it.

## Note

This is defensive anti-cheat analysis of a clean official build. Do not
distribute game binaries, decrypted assets, or a working cheat.
