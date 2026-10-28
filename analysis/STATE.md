# Free Fire MAX 2.133.1 — Analysis State (saved 2026-10-28)

## Objective

Determine the client-side mechanic used for the reported cheat pattern:

> first bullet hits body, subsequent bullets hit head while holding fire

The supplied XAPK is the **clean/official** build (`com.dts.freefiremax`, version
`2.133.1`, versionCode `2019118527`, Unity IL2CPP). The cheat is not in the APK.
The goal is to identify which client surface a cheat would have to abuse, and
whether that abuse is practical.

## Status

- Metadata is decrypted and fully parseable.
- `libil2cpp.so` is protected (`WARNING: find .init_proc`,
  `ERROR: This file may be protected`), so Il2CppDumper fails while generating
  `script.json` / `dump.cs` for game types.
- We worked around that by parsing the metadata directly and resolving
  `Il2CppType` entries from the ELF after applying `R_AARCH64_RELATIVE`
  relocations. This is reliable for type/field/method names and signatures.
- Several concrete cheat vectors were identified. The strongest match for the
  exact "first body, then head" pattern is **client-side aim/aim-assist
  override**, with **hit-collider-type spoofing** as the strongest alternative.
- A draft report is in `analysis/reports/report-draft.md`.

## Artifacts / paths

Persistent copies (this directory survives reboot):

```
analysis/
  STATE.md                         <- this file
  scripts/
    dump_type_resolved.py          <- main metadata + ELF type dumper
    mdparse.py                     <- metadata header/type parser
    findmembers.py                 <- field/method keyword search
    dump_type.py                   <- older dumper (40-byte method stride)
    literals.py                    <- string-literal search
    disasm.py                      <- capstone/pyelftools disassembler
    decrypt_metadata.py            <- XOR 0xE8 metadata decryptor
  data/
    global-metadata.dec.dat        <- decrypted metadata (55 MB)
    assembly-csharp-patch.enc.bin  <- decompressed encrypted iFix patch bundle
  outputs/                         <- saved dumps/searches (see below)
  reports/
    report-draft.md
  gh-repo-reference/
    analyze.py, analyze.yml, README.md
```

Original game files (already on disk):

```
/home/shrawan/experiments/hackathon/ff.dts.hackathon.batch3.custom.same.package.xapk
/home/shrawan/experiments/hackathon/extracted/work/config/lib/arm64-v8a/libil2cpp.so
/home/shrawan/experiments/hackathon/extracted/work/asset/assets/bin/Data/Managed/Metadata/global-metadata.dat
```

The original `global-metadata.dat` is XOR-encrypted with key `0xE8`.
`scripts/decrypt_metadata.py` regenerates the decrypted file.

GitHub repo: `https://github.com/Shrawan-13/ff-dts-analysis`
- public, branch `main`
- release tag `input` contains the 427 MB XAPK
- current workflow is still dumper-dependent and fails; see "Next steps".

## Metadata format notes (IL2CPP v31)

Header is 60 little-endian `uint32` values. Key offsets used:

- `H[6]` = string literal/string data offset (used as string base)
- `H[12]` = methods offset
- `H[24]` = fields offset
- `H[40]` = type definitions offset
- `H[41]` = type definitions size; `NT = size / 88`
- `H[22]` = parameters offset
- `H[23]` = parameters size; each parameter is 12 bytes

Struct strides:

- TypeDefinition: **88 bytes** (`<16I8H2I`); name at +0, namespace at +4,
  fieldStart at +32, methodStart at +36, method_count at +64, field_count at +72
- MethodDefinition: **40 bytes** (`<10I`), not 36
  - `raw[0]` nameIndex
  - `raw[1]` declaringType
  - `raw[2]` returnType
  - `raw[4]` parameterStart (`0xFFFFFFFF` = none)
  - `raw[7]` token
  - `raw[9]` = `(parameterCount << 16) | slot`
- FieldDefinition: **12 bytes** (`<3I`): nameIndex, typeIndex, token
- ParameterDefinition: **12 bytes** (`<3I`): nameIndex, token, typeIndex

## ELF / type-table resolution

`libil2cpp.so` is a PIE with these relevant `PT_LOAD` mappings (vaddr, offset):

- `0x0000000000000000` -> file `0x0`
- `0x000000000329d00c` -> file `0x329900c`
- `0x000000000a556560` -> file `0xa54e560` (RW, `.data.rel.ro`)
- `0x000000000a9fe510` -> file `0xa9f2510`
- more segments after that

Important: the dumper-printed addresses are **virtual addresses**, not file
offsets. Example: `MetadataRegistration` is at VA `0xa705468`; its file offset is
`0xa6fd468` (subtract `0x8000` for the `0xa556560` segment).

`Il2CppMetadataRegistration` at VA `0xa705468`:

- counts are valid; pointer fields are zero in the raw file and filled by
  relocations at runtime.
- `typesCount` at `MR + 0x30` = `0x1973b` = **104251**
- `types` pointer at `MR + 0x38` resolves (via relocation addend) to
  **`0xa77a8a8`**

`dump_type_resolved.py`:

1. Parses ELF program headers and builds VA -> file offset mapping.
2. Iterates relocation sections, keeps `R_AARCH64_RELATIVE` (`r_info_type == 1027`)
   as `r_offset -> r_addend`.
3. `ptr(va)` returns the relocation addend if present, else reads the raw qword.
4. Resolves `Il2CppType`:
   - `type = (bits >> 16) & 0xff`
   - class/value type (`0x11`, `0x12`): `datapoint` is a TypeDefinition index
   - generic instance (`0x15`): `Il2CppGenericClass` -> typeDefinitionIndex + classInst
   - SZARRAY (`0x1d`): pointer to element type
   - `0x0e` string, primitives map to names
5. Prints fields with resolved types, methods with return type + parameter count.

Run:

```bash
cd /home/shrawan/experiments/hackathon/analysis
source /tmp/opencode/unityenv/bin/activate   # if it still exists
# if the venv was wiped, create one: python3 -m venv /tmp/opencode/unityenv && \
#   /tmp/opencode/unityenv/bin/pip install pyelftools
python3 scripts/dump_type_resolved.py 32128
python3 scripts/dump_type_resolved.py '32128:aim|assist|head|hit|damage|rotation'
```

`FF_META` and `FF_BIN` environment variables override the default paths.

## Key type indices

| Index | Type | Notes |
|---:|---|---|
| 32128 | `COW.GamePlay.Player` | 1692 fields, 4143 methods |
| 34569 | `COW.GamePlay.HitDetectColliderHelper` | `IsPlayerHead`, `ColliderType` |
| 34272 | `COW.GamePlay.HNLIMBLIANL` | damage info; field `BGMOAOCFPGM` = `EHGMCNBHNMD` |
| 34568 | `COW.GamePlay.EHGMCNBHNMD` | enum: `Head`, `Body`, `Limb`, ... |
| 438 | `.ColliderInfo` | `m_collider`, `m_hitBoxType` (`.HitPart`) |
| 439 | `.HitPart` | `Head`, `Neck`, `Chest`, `Hips`, ... |
| 32214 | `COW.GamePlay.OGKFEMJNCGM` | aim-assist target interface |
| 34606 | `COW.GamePlay.NLIMDENAFNN` | `Player.m_AimAssist` type |
| 34612 | `COW.GamePlay.DCIDAEHLHPI` | `GetAimAssistOnSighting` return |
| 34614 | `COW.GamePlay.PLOAJDMCLGB` | `m_AimAssistForIceWall` |
| 11882 | `COW.WeaponGunFeelProfileData` | `strongAimAssistShot`, soft-assist curves |
| 11875 | `COW.WeaponAimAssistAutoAbsorbData` | auto-absorb config |
| 13096 | `COW.UGCAttachmentRepItem` | `SightAimAssist*` setters |
| 13085 | `COW.UGCAimAssistEntityRepItem` | `AimAssistDistance`, `AimAssistCenterOffset` |
| 35663 | `COW.GamePlay.UGCAimAssistEntity` | UGC aim-assist entity |
| 32146 | `COW.GamePlay.BigHeadComponent` | head `CapsuleCollider`, `UpdateScale` |
| 11147 | `COW.BigHeadData` | `HeadScale`, `HeadShotDamageScale` |
| 11057 | `COW.BodyPartUtilByName` | `SetBoneDynamicScale`, `AddOrUpdateBoneScale` |
| 31222 | `COW.Gameplay.UGC.UGCSkeletonCustomHitBox` | `EnableCustomHitBox` |
| 31399 | `COW.Gameplay.UGC.UGCLocalColliderIntegrityValidator` | UGC collider SHA1 check |
| 31407 | `COW.Gameplay.UGC.UGCResBodyPartDef` | UGC body-part defs |
| 23231 | `COW.SettingDetail` | `aim_assist`, `use_auxaim`, `aux_aim_sensitivity` |
| 12010 | `COW.GameModeSetting` | `BanAimAssist`, `EnableBigHead`, `FireCollider*` |
| 12013 | `COW.GameVarDef` | debug aim-assist vars, `UseSniperCollider`, anti-cheat flags |
| 34846 | `COW.GamePlay.PlayerAttributes` | `BuffEcaWeaponAimAssist*` |
| 36645 | `GCommon.InjectFixManager` | iFix patch loader |
| 43247 | `IFix.Core.PatchManager` | `Load(string filepath)` |

## Findings / candidate cheat vectors

### Vector A — client-side aim / aim-assist override (best match)

Evidence:

- `Player.get_HeadCollider()` -> `UnityEngine.Collider`
- `Player.GetHeadTF()` and `Player.get_HeadBoneTransform()` -> `UnityEngine.Transform`
- `Player.SetAimRotation(UnityEngine.Quaternion, bool)`
- `Player.GetAimRotation()` / `Player.GetAuxAimRotation()` -> `Quaternion`
- `Player.UpdateAiming(float, float, bool)`
- `Player.m_CurrentAimRotation` field
- `Player.CallSetAimRotationCount` field (possible anti-cheat signal)
- `Player.GetHeuristicTarget()` -> `COW.GamePlay.OGKFEMJNCGM`
- `Player.HasHeuristicTarget()`, `Player.GetHeuristicTargetInfoScore()`
- `Player.SetEAimAssitMode(COW.EAimAssist)`; enum has `AllOn`, `OffOnSighting`, `AllOff`
- `Player.GetAimAssistOnSighting()` -> `COW.GamePlay.DCIDAEHLHPI`
- `Player.GetAimAssistDampCoefficient(weapon)` -> float
- `Player.IsNeedAimAssists()`, `Player.get_CanBeLockedByAimAssist()`,
  `Player.get_IsBanAimAssistState()`, `Player.get_IgnoreAimAssistType()`
- Target interface `OGKFEMJNCGM` has:
  - `GetAttackableCenterWS()` -> Vector3
  - `GetHitDamagePos()` -> Vector3
  - `get_LockedAimingCollider()` / `set_LockedAimingCollider(Collider)`
  - `NeedAssit()`, `CanAssitByWeapon(...)`, `get_CanBeLockedByAimAssist()`
- `WeaponGunFeelProfileData` has `strongAimAssistShot` (uint),
  `enableSoftAssist`, `softAssistTargetKeepTime`,
  `softAssistSequentialSmoothingTime`, `softAssistInputThreshold`,
  `softAssistInputAttenuation`, `softAssistLostStrengthScale`,
  `hipSoftAssist*`, `adsSoftAssist*`, `adsSoftAssistMaxYawPerShot`,
  `hipSoftAssistMaxPitchPerShot`, etc.
- `UGCAttachmentRepItem` has public setters:
  `SightAimAssist`, `SightAimAssistSnapRange`, `SightAimAssistDistFalloff`,
  `SightAimAssistDistpriority`, `SightAimAssistDistprioMin/Max/Coef`,
  `SightRotSensitiveness`.
- Config keys in string literals: `aim_assist`, `aim_assist_lock_keep_time`,
  `aim_assist_lock_decrease_time`, `aim_assist_max_screen_range`,
  `aim_assist_min_screen_range`, `aim_assist_specified`,
  `can_aimassist`, `sight_aim_assist*`, `use_auxaim`, `aux_aim_sensitivity`.
- Debug vars in `GameVarDef`: `DebugWeaponAimAssistMaxScore`,
  `DebugWeaponAimAssistMinScore`, `DebugWeaponAimAssistDampCoefficient`,
  `DebugWeaponAimAssistDampYSensitivity`.

Why it matches the pattern:

1. The cheat acquires a target on the first shot (body/center).
2. It sets the target's `LockedAimingCollider` to the target's head collider
   (or computes a quaternion to `HeadBoneTransform`/`GetHeadTF` and calls
   `SetAimRotation`).
3. Holding fire keeps the aim/soft-assist locked on the head for subsequent
   shots.

Practicality: **high** as a client-side vector. The client computes the shot
direction; the server must validate the angle delta and the claimed hit. The
first-shot body is consistent with target acquisition or a deliberate delay.

### Vector B — hit-collider-type / body-part spoof (strong alternative)

Evidence:

- `HitDetectColliderHelper` fields: `ColliderType` (`EHGMCNBHNMD`),
  `OCHLCHLHLJC` (`OGKFEMJNCGM`), `MBIDECIOIBM` (`GameObject`).
- `HitDetectColliderHelper.IsPlayerHead()` -> bool.
- `ColliderInfo.m_hitBoxType` is `.HitPart` (`Head`, `Neck`, `Chest`, ...).
- `HNLIMBLIANL` (damage info) has `BGMOAOCFPGM` of type `EHGMCNBHNMD`
  (`Head`, `Body`, `Limb`, ...).
- `Player.TakeDamage` overloads:
  - `void TakeDamage(HNLIMBLIANL, PIAEKELILCJ, <delegate>, uint)`
  - `int TakeDamage(int, BEADLMGGGGL, HNLIMBLIANL, int, Vector3, Vector3,
    <delegate>, PIAEKELILCJ, uint)`
- `message.LPJEFLJOJCM` enum: `EHITBODYPART_HEAD`, `EHITBODYPART_BODY`,
  `EHITBODYPART_LIMB`, ...
- `message.MHHELEDEJHG` has a `HitBodyPart` enum value; `COW.MatchModelKillData`
  has `hitBodyPart`.

Why it matches: a cheat can relabel a body collider as `Head` (or set
`HitDetectColliderHelper.ColliderType = EHGMCNBHNMD.Head`) so body hits are
reported as headshots. The "first body, rest head" pattern could be a delayed
toggle after the first hit. If the server trusts the client's hit part, this is
trivial.

Practicality: **high** if the server accepts the client's `EHITBODYPART`/
collider type; **medium** if the server recomputes from the shot vector. The
client-side `TakeDamage` path and damage-info body-part field are present, so
this is a real attack surface.

### Vector C — big-head / head-bone scaling (direct headshot vector)

Evidence:

- `COW.GamePlay.BigHeadComponent` fields:
  - `HCMNGNGFCIC` float
  - `OLAPDAPHKIE` `UnityEngine.Transform` (head bone)
  - `GFCGPPKLKEP` `UnityEngine.CapsuleCollider` (head collider)
  - `KHHAACKCJKE` `UnityEngine.Vector3`
  - methods `get_scaleValue()`, `UpdateScale(float)`,
    `SetNeckRevertScaleMult(float)`, `LateUpdate()`
- `COW.BigHeadData`: `HeadScale`, `HeadShotDamageScale`, `HeadAvatar`,
  `EffectID`, etc.
- `Player.IsInBigHeadScale()`, `Player.GetBigHeadScale()`,
  `Player.ApplyBigHeadScalePreHangLateUpdate()`,
  `Player.PlayBigHeadHypeEffect()`, `Player.PlayBigHeadLevelUpEffect()`.
- `BodyPartUtilByName`: `SetBoneDynamicScale(3)`, `AddOrUpdateBoneScale(2)`,
  `setAllBoneScale()`, `ControlBoneWorldRotation(2)`.
- UGC: `UGCSkeletonCustomHitBox.EnableCustomHitBox(3)` returns
  `CapsuleCollider`; `UGCPlayerRepItem.HeadBonesScale`; `UGCResBodyPartDef`.
- `GameModeSetting.EnableBigHead`, `BigHeadCameraBackTriggerScale`,
  `BigHeadCameraBackOffset`; `GameVarDef.EnableBigHeadResetHangmanager`.
- String literals: `BigHead`, `HeadScale`, `HeadShotDamageScale`,
  `'BigHeadComponent no find bone_Head gameobject in entity'`.

Why it matches: enlarging the head collider/bone makes headshots much easier.
A cheat can call `BigHeadComponent.UpdateScale(large)` on enemies or
`BodyPartUtilByName.SetBoneDynamicScale` on the head bone. The "first body,
then head" could be a scale toggle after the first shot.

Practicality: **high** for the client-side collider; **medium** in normal
matches if big-head is mode-gated or server-validated. Very relevant to
UGC/custom rooms.

### Vector D — UGC custom hitboxes / aim-assist entities

Evidence:

- `UGCSkeletonCustomHitBox.ApplyCustomBoxRecursively(3)`,
  `GetHitBoxChild(2)`, `EnableCustomHitBox(3)` -> `CapsuleCollider`.
- `UGCResBodyPartDef.LoadFromData(bool)`; `message.JDGLHIMBCAF` data.
- `UGCAimAssistEntityRepItem.AimAssistDistance` (float) and
  `AimAssistCenterOffset` (Vector3) with public setters.
- `UGCAimAssistEntity` fields: `UGCAimAssistEntityRepItem`, `Transform`,
  bool, `Collider`; methods `GetAttackableCenterWS`, `GetHitDamagePos`,
  `set_LockedAimingCollider`, `CanAssistByUGC(bool)`, `TakeDamage(4)`.
- `HitDetectColliderHelper.IsUGCAimAssistPart()`.
- `UGCLocalColliderIntegrityValidator.Validate(2)`;
  string literals:
  - `ColliderCommon SHA1 mismatch`
  - `UGC game loading: Local ColliderCommon integrity check failed, ErrorType: ... EnableLocalColliderAntiHack: ...`
  - `UGC game loading: Local ColliderCommon integrity check failed, force ending process`
- `GameVarDef.EnableLocalColliderValidation`,
  `GameVarDef.EnableLocalColliderAntiHack`.

Why it matches: a malicious UGC map can define a body part as head, place an
aim-assist entity at the head with a large `AimAssistDistance`, or enlarge the
head bone. The local SHA1 validator is the mitigation; `EnableLocalColliderAntiHack`
is a config flag a cheat could try to disable.

Practicality: **high for UGC/custom rooms**, lower for official BR/CS maps
unless the same code paths are reachable.

### Vector E — iFix runtime patching (persistence / bypass)

Evidence:

- `GCommon.InjectFixManager`:
  - `LoadPatch(GCommon.ResourceID[] codePatchResIDs)`
  - `LoadPatch(string patchFileAb)`
  - `LoadTestPatch()`
  - `Support()`
- `IFix.Core.PatchManager`:
  - `Load(string filepath)` -> `VirtualMachine`
  - `Load(Stream, bool)`
  - `Load(byte[], int, bool)`
  - `TestOptimizeLoad(...)`, `OptimizeLoad(...)`
- `IFix.Core.IFixCSVData` maps `DeclaringType`, `MethodName`, `ParamCount`,
  `PosId`, `AttributeID`, versions; `IDMAP0..4` method-id maps.
- `Player.<>iFixBaseProxy_TakeDamage` and
  `Player.<>iFixBaseProxy_get_CanBeLockedByAimAssist` exist — the game itself
  iFix-patches these methods.
- `assembly-csharp-patch` UnityFS bundle is encrypted; UnityPy reports
  `key_sig=b'd442e25cd401db5b'`, `data_sig=b'\x00\x00\x00\x04CAB-fb083c06'`.
  We could not decrypt it with metadata/libil2cpp-derived keys.
- No signature/verification method is visible in the iFix metadata. The loader
  accepts a file path or stream.

Why it matches: a cheat can load its own iFix patch (or replace the patch
bundle) to modify `SetAimRotation`, `GetHeuristicTarget`, `TakeDamage`,
`IsPlayerHead`, `CanBeLockedByAimAssist`, etc. at runtime. This explains why
server-side code updates do not remove the cheat.

Practicality: **high** if the loader is reachable and does not verify patch
authenticity. This is a general code-patching vector, not a specific headshot
mechanic, but it is the likely persistence layer.

### Vector F — config/debug-variable tampering

Evidence:

- `COW.SettingDetail`: `aim_assist` (int), `aux_aim_sensitivity` (float),
  `use_auxaim` (int), `use_auxaim_parachute/dash/drive`, `damage_setting`.
- `GameModeSetting`: `BanAimAssist`, `EnableVehicleAimAssist`,
  `CheckGunFeelSoftAssist`, `EnableBigHead`, `EnableFireColliderScale`,
  `FireColliderRadiusScale`, `FireColliderHeightScale`,
  `AimAssistKnockDownParam`, `DisableAimAssistReviveParachutingTarget`,
  `AIAimAssistWeight`, `IsHeadShotOnly`, `EnableHitTagHackCheck`.
- `GameVarDef`: `DebugWeaponAimAssistMaxScore`,
  `DebugWeaponAimAssistMinScore`, `DebugWeaponAimAssistDampCoefficient`,
  `DebugWeaponAimAssistDampYSensitivity`, `EnableAimAssistChange`,
  `EnableStropAimAssist`, `NoHeadshotTimeAfterPoseSwitch`,
  `UseSniperCollider`, `UseWeaponExtraHitboxConfig`,
  `EnableLocalColliderValidation`, `EnableLocalColliderAntiHack`,
  `HitDamageRatioHead`, `HitDamageRatioBody`, `HitDamageRatioLimb`.
- String keys: `extra_hitbox_enable`, `extra_hitbox_size`,
  `extra_hitbox_armor_enable`, `extra_hitbox_damage_ratio`,
  `headshot_min_ratio`, `headshot_full_ratio_distance`,
  `headshot_min_ratio_distance`, `shield_damge_by_bodypart`,
  `use_snipercollider_whensighting`.

Why it matches: if these are active in release, a cheat can set the snap range,
soft-assist strength, head damage ratio, or extra hitbox size via config/memory.
`extra_hitbox_*` is especially interesting: an extra hitbox with a large size
and head damage ratio could directly produce headshots.

Practicality: **medium** — presence in metadata does not prove release
activation or server authority. Worth verifying with a runtime test or a
config-diff.

## What failed / caveats

- Il2CppDumper v6.7.46 crashes in `Il2CppExecutor.GetMethodSpecName`
  (`System.IndexOutOfRangeException`) on this protected binary. It writes only
  a ~55 KB incomplete `dump.cs`; `script.json` and `stringliteral.json` are
  missing. Do not depend on it.
- The binary is protected; static method pointers/code registration are not
  trustworthy. Names/fields/signatures from metadata are trustworthy.
- `assembly-csharp-patch` decryption key was not found. The iFix patch format
  is understood, but the bundle contents are not.
- We have not yet confirmed the exact in-match network payload that carries
  `EHITBODYPART`. The `message` protobuf classes are obfuscated; the enum and
  kill-data field are visible, but the payload field name was not located.
- We have not proven server trust. The report should distinguish
  "client-side surface exists" from "server accepts it".

## Next steps (priority order)

1. **Confirm the network hit/fire payload.** Search `message` types for fields
   of type `HNLIMBLIANL`, `EHGMCNBHNMD`, or `EHITBODYPART`; inspect
   `TakeDamage` callers and the RUDP send path. If the client sends the body
   part, Vector B is confirmed as a server-trust issue.
2. **Confirm the aim-assist lock path.** Dump `NLIMDENAFNN` and `OGKFEMJNCGM`
   methods with parameter types; find who calls
   `set_LockedAimingCollider` and `SetAimRotation`. Determine whether the
   locked collider is used for the shot ray or only for camera assist.
3. **Test the big-head path.** Check whether `BigHeadComponent` is present on
   enemies in normal modes, and whether `UpdateScale` changes the hit collider
   used by `HitDetectColliderHelper`.
4. **Inspect iFix integrity.** Search `IFix.Core` for signature/hash checks;
   inspect `InjectFixManager.LoadPatch` and `PatchManager.Load` callers. Check
   whether the patch bundle is authenticated.
5. **Fix the GitHub Actions workflow.** Remove the Il2CppDumper dependency and
   make the run metadata-only (decrypt metadata + run
   `dump_type_resolved.py`/report generator). Keep `actions/cache` for the
   XAPK/metadata. The current workflow fails at `test -s out/script.json`.
6. **Write the final report** from `reports/report-draft.md`, with a clear
   distinction between confirmed client surfaces and unconfirmed server trust.
7. **Push** the report/scripts (not the 55 MB metadata or game binaries) to
   `Shrawan-13/ff-dts-analysis`.

## Resume commands

```bash
cd /home/shrawan/experiments/hackathon/analysis
# If the venv is gone:
python3 -m venv /tmp/opencode/unityenv
/tmp/opencode/unityenv/bin/pip install pyelftools
source /tmp/opencode/unityenv/bin/activate

# Dump a type with resolved field/method types:
python3 scripts/dump_type_resolved.py 32128
python3 scripts/dump_type_resolved.py '32128:aim|assist|head|hit|damage'

# Search fields/methods by keyword (uses /tmp paths; adjust if needed):
python3 scripts/findmembers.py aim_assist
```

## GitHub status

- Repo: `https://github.com/Shrawan-13/ff-dts-analysis`
- Analysis state/report/scripts pushed on 2026-10-28 in commit `8c8dfcc`
  (`main`), under `analysis/`. The 55 MB decrypted metadata and the encrypted
  patch bundle are **not** committed.
- Token: retrieve from keyring with
  `secret-tool lookup service gh:github.com username Shrawan-13`
  (do not print/persist it).
- Release `input` has the 427 MB XAPK.
- Workflow `.github/workflows/analyze.yml` currently expects
  `out/script.json` from Il2CppDumper and fails. Fix before the next run.
- Artifact `il2cpp-dump` contains only `dump.cs` + `dumper.log`.

## Ethics / framing

This analysis is for defensive anti-cheat work on a clean official build. The
report should describe attack surfaces and mitigations, not provide a
ready-to-use cheat. Do not distribute game binaries or decrypted assets beyond
the private analysis workspace.
