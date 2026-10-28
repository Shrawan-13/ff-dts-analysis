# Free Fire MAX 2.133.1 — Client-Side Headshot Cheat Feasibility and QA Validation Report

**Document status:** Final draft for QA / security / management review  
**Date:** 2026-10-28  
**Scope:** clean official XAPK, `com.dts.freefiremax`, version `2.133.1`,
versionCode `2019118527`, Unity IL2CPP  
**Classification:** Internal anti-cheat analysis — do not distribute as a cheat

---

## 0. Management summary

**Question:** Is the reported cheat — first bullet body, subsequent bullets
headshots while holding fire — actually possible?

**Answer:** The clean client contains every client-side primitive needed to
attempt it. We have **static proof** of those primitives (32/32 metadata checks
pass). We do **not** yet have **dynamic proof** that the live server accepts
them. That is the missing piece, and it is exactly what the attached QA plan is
designed to produce.

| Claim | Evidence | Status |
|---|---|---|
| Client exposes head collider / head bone | `Player.get_HeadCollider`, `get_HeadBoneTransform`, `GetHeadTF` | **PROVEN (static)** |
| Client can write aim rotation | `SetAimRotation`, `m_CurrentAimRotation`, `UpdateAiming` | **PROVEN (static)** |
| Aim-assist target has a lockable collider | `OGKFEMJNCGM.set_LockedAimingCollider` | **PROVEN (static)** |
| Client carries a hit body-part type | `ColliderInfo.m_hitBoxType`, `EHGMCNBHNMD`, `HNLIMBLIANL` | **PROVEN (static)** |
| Client can scale the head | `BigHeadComponent.UpdateScale`, `BodyPartUtilByName` | **PROVEN (static)** |
| Client has a runtime patch loader | `IFix.Core.PatchManager.Load`, `InjectFixManager.LoadPatch` | **PROVEN (static)** |
| Server trusts the client’s hit part | — | **UNKNOWN — needs dynamic test** |
| Server accepts client aim direction | — | **UNKNOWN — needs dynamic test** |
| Big-head scale affects live hit registration | — | **UNKNOWN — needs dynamic test** |
| Unsigned iFix patch is accepted | — | **UNKNOWN — needs dynamic test** |
| The exact “first body, then head” pattern works live | — | **NOT PROVEN — needs end-to-end test** |

**Recommendation:** approve a controlled, authorized QA test using a private
server and instrumented client. Do not claim live exploitability until the
dynamic tests in `qa-test-plan.md` pass. If they fail, the corresponding vector
is mitigated and should be documented as such.

**Most likely vector:** A — aim-assist lock / aim-rotation override. The first
shot acquires the target at body/center; subsequent shots lock the aim-assist
collider to the head.

**Strongest alternative:** B — hit-collider-type / body-part spoof. A body hit
is reported as `Head`; this only works if the server trusts the client’s hit
part.

**Other direct headshot vectors:** C — big-head / head-bone scaling;
D — UGC custom hitboxes and UGC aim-assist entities; E — iFix runtime patches
(persistence); F — config/debug-variable tampering (enabler).

---

## 1. Scope, definitions, and limits

### 1.1 What “possible” means

We separate three claims:

1. **Client-side possible** — the client contains the data and methods needed
   to attempt the behavior. This is what static metadata can prove.
2. **Live-practical** — the server accepts the resulting shot/hit and the
   behavior survives normal anti-cheat. This requires a dynamic test.
3. **Undetected** — the behavior does not trigger telemetry or enforcement.
   This requires a detection/anti-cheat test.

This report proves (1) and specifies the tests for (2) and (3).

### 1.2 What the clean APK can and cannot prove

The supplied XAPK is the **clean official build**. It does not contain the
cheat. It does contain the game’s own aim-assist, hit-detection, damage, head
scaling, and patch-loading code. Metadata names and signatures are readable
even though the native binary is protected.

The APK **cannot** prove:

- whether the server recomputes the hit from the shot vector or trusts the
  client’s hit result;
- whether the server validates the body part or damage event;
- whether the live anti-cheat detects modified clients, iFix patches, or
  collider changes;
- whether debug/config paths are active in release.

Those are server/anti-cheat questions and must be tested dynamically.

### 1.3 Ethical and legal boundary

This is a defensive anti-cheat analysis. The QA plan is for an **authorized
private test environment** with test accounts and written approval. It is not a
guide to cheating in production, and it does not include cheat code, offsets,
injection steps, or anti-cheat bypasses. The security team owns any
instrumented test client.

---

## 2. Method and reproducibility

### 2.1 Metadata extraction

- `global-metadata.dat` is XOR-encrypted with key `0xE8`; decrypted magic
  `0xFAB11BAF`, version 31.
- 43,956 type definitions; 104,251 `Il2CppType` entries.
- Type definitions: 88-byte stride.
- Methods: **40-byte** stride (not 36).
- Fields: 12-byte stride.
- Parameters: 12-byte stride.

### 2.2 Type resolution

Il2CppDumper v6.7.46 crashes on this protected binary
(`System.IndexOutOfRangeException` in `Il2CppExecutor.GetMethodSpecName`), so
we resolve types directly:

- `Il2CppMetadataRegistration` at VA `0xa705468` (file offset `0xa6fd468`).
- `typesCount` = `0x1973b` = 104,251.
- `types` pointer resolves to `0xa77a8a8` after applying
  `R_AARCH64_RELATIVE` relocations from the ELF.
- `dump_type_resolved.py` maps VA→file offset and resolves
  class/value/generic/array/primitive types.

### 2.3 Static evidence verifier

`scripts/verify_evidence.py` checks that the metadata actually contains every
type, field, method, and config string cited in this report.

```bash
cd /home/shrawan/experiments/hackathon/analysis
python3 scripts/verify_evidence.py
```

Expected result:

```
Summary: 32 passed, 0 failed
```

The full output is in `outputs/evidence-verification.txt` and Appendix A.
This proves the **static surface**, not live exploitability.

### 2.4 Artifacts

- `analysis/STATE.md` — full working state and next steps.
- `analysis/scripts/dump_type_resolved.py` — metadata + ELF type dumper.
- `analysis/scripts/verify_evidence.py` — static evidence verifier.
- `analysis/outputs/` — saved dumps and searches.
- `analysis/reports/qa-test-plan.md` — dynamic QA validation plan.

---

## 3. Threat model

**Attacker capability assumed for QA:**

- A modified/instrumented client on a test device.
- Ability to observe and exercise client-side aim, hit-detection, damage, head
  scaling, and patch-loading surfaces.
- Ability to capture packets between client and a private test server.
- No access to server source code or production infrastructure.

**Assets the client exposes:**

- Head collider and head bone transform.
- Aim rotation and aux-aim rotation.
- Aim-assist target and lockable collider.
- Hit collider type and per-bone hit part.
- Damage info carrying the collider/body part.
- Head scale and bone scale.
- iFix patch loader.
- Config/debug variables for aim assist and extra hitboxes.

**Trust boundary:** the server. Every vector reduces to one question: does the
server accept the client’s aim/hit/damage claim, or does it recompute it?

---

## 4. Static evidence by vector

### Vector A — Aim-assist lock / aim-rotation override

**Confirmed client surface:**

| Member | Signature / type |
|---|---|
| `Player.get_HeadCollider` | `UnityEngine.Collider` |
| `Player.get_HeadBoneTransform` | `UnityEngine.Transform` |
| `Player.GetHeadTF` | `UnityEngine.Transform` |
| `Player.SetAimRotation` | `void(Quaternion, bool)` |
| `Player.GetAimRotation` | `Quaternion` |
| `Player.GetAuxAimRotation` | `Quaternion` |
| `Player.ResetAuxAimRotation` | `void()` |
| `Player.UpdateAiming` | `void(float, float, bool)` |
| `Player.GetHeuristicTarget` | `OGKFEMJNCGM` |
| `Player.GetHeuristicTargetInfoScore` | `float` |
| `Player.SetEAimAssitMode` | `void(COW.EAimAssist)` |
| `Player.GetAimAssistOnSighting` | `COW.GamePlay.DCIDAEHLHPI` |
| `Player.GetAimAssistDampCoefficient` | `float(HBIBDMMOOOK)` |
| `Player.IsNeedAimAssists` | `bool` |
| `Player.get_CanBeLockedByAimAssist` | `bool` |
| `Player.get_IsBanAimAssistState` | `bool` |
| `Player.get_IgnoreAimAssistType` | `uint` |

`OGKFEMJNCGM` (aim-assist target) exposes:

```
Vector3 GetAttackableCenterWS()
Vector3 GetHitDamagePos()
Collider get_LockedAimingCollider()
void     set_LockedAimingCollider(Collider)
bool     NeedAssit()
bool     CanAssitByWeapon(...)
bool     get_CanBeLockedByAimAssist()
```

`COW.EAimAssist` has `AllOn`, `OffOnSighting`, `AllOff`.

Weapon-side assist data:

- `WeaponGunFeelProfileData.strongAimAssistShot` (`uint`)
- `enableSoftAssist` (`bool`)
- `softAssistTargetKeepTime`, `softAssistSequentialSmoothingTime`,
  `softAssistInputThreshold`, `softAssistInputAttenuation`,
  `softAssistLostStrengthScale`
- `hipSoftAssist*` / `adsSoftAssist*` curves, angles, and strengths.

Attachment/sight setters (`UGCAttachmentRepItem`):

```
SightAimAssist                 bool
SightAimAssistSnapRange        float
SightAimAssistDistFalloff      float
SightAimAssistDistpriority     bool
SightAimAssistDistprioMin      float
SightAimAssistDistprioMax      float
SightAimAssistDistprioCoef     float
SightRotSensitiveness          float
```

Config keys: `aim_assist`, `aim_assist_lock_keep_time`,
`aim_assist_lock_decrease_time`, `aim_assist_max_screen_range`,
`aim_assist_min_screen_range`, `aim_assist_specified`, `can_aimassist`,
`sight_aim_assist*`, `use_auxaim`, `aux_aim_sensitivity`.

**Attack concept:** acquire a target on the first shot, then lock the
aim-assist collider to the target’s head collider, or compute a rotation to the
head bone and write it through the aim rotation path. Holding fire keeps the
aim on the head.

**Why it matches the reported pattern:** first shot = target acquisition at
body/center; subsequent shots = head lock. This is the most natural explanation
for “first body, then head.”

**What must be true for it to work live:** the server must accept the client’s
shot direction (within its validation tolerance). If the server recomputes from
the client’s shot vector, aiming at the head still works; if it rejects large
angle deltas, the lock must be gradual or within tolerance.

**Confidence:** high that the surface exists; medium-high that it is the exact
observed mechanic.

---

### Vector B — Hit-collider-type / body-part spoof

**Confirmed client surface:**

- `HitDetectColliderHelper`:
  - `ColliderType` (`EHGMCNBHNMD`)
  - `IsPlayerHead()`
  - `IsUGCAimAssistPart()`
- `ColliderInfo.m_hitBoxType` is `.HitPart` (`Head`, `Neck`, `Chest`, ...).
- `EHGMCNBHNMD`: `Head`, `Body`, `Limb`, `Vehicle`, `Protection`, ...
- `HNLIMBLIANL` (damage info) has `BGMOAOCFPGM` of type `EHGMCNBHNMD`.
- `Player.TakeDamage`:
  - `void(HNLIMBLIANL, PIAEKELILCJ, <delegate>, uint)`
  - `int(int, BEADLMGGGGL, HNLIMBLIANL, int, Vector3, Vector3,
    <delegate>, PIAEKELILCJ, uint)`
- `message.LPJEFLJOJCM`: `EHITBODYPART_HEAD`, `EHITBODYPART_BODY`,
  `EHITBODYPART_LIMB`, ...
- `message.MHHELEDEJHG` has `HitBodyPart`; `COW.MatchModelKillData` has
  `hitBodyPart`.

**Attack concept:** make a body collider report `Head`, or construct damage
info with `Head`, or force `IsPlayerHead()` true. If the server trusts the
client’s body part, body hits become headshots.

**Why it could match the pattern:** a delayed toggle after the first hit would
produce first-body-then-head; a static relabel would make all shots headshots.

**What must be true for it to work live:** the server must trust the client’s
`EHITBODYPART` / collider type. If it recomputes from its own hitboxes, this
fails.

**Confidence:** high that the client can spoof; medium that the server trusts
it. This is the first vector to test dynamically.

---

### Vector C — Big-head / head-bone scaling

**Confirmed client surface:**

- `BigHeadComponent`:
  - `HCMNGNGFCIC` (`float`)
  - `OLAPDAPHKIE` (`Transform`, head bone)
  - `GFCGPPKLKEP` (`CapsuleCollider`, head collider)
  - `KHHAACKCJKE` (`Vector3`)
  - `float get_scaleValue()`
  - `void UpdateScale(float)`
  - `void SetNeckRevertScaleMult(float)`
- `BigHeadData`: `HeadScale`, `HeadShotDamageScale`, `HeadAvatar`, ...
- `Player.IsInBigHeadScale()`, `GetBigHeadScale()`,
  `ApplyBigHeadScalePreHangLateUpdate()`.
- `BodyPartUtilByName.SetBoneDynamicScale(3)`,
  `AddOrUpdateBoneScale(2)`, `setAllBoneScale()`.
- UGC: `UGCSkeletonCustomHitBox.EnableCustomHitBox(3)`,
  `UGCPlayerRepItem.HeadBonesScale`, `UGCResBodyPartDef.LoadFromData(bool)`.
- `GameModeSetting.EnableBigHead`, `BigHeadCameraBackTriggerScale`.
- String literal: `'BigHeadComponent no find bone_Head gameobject in entity'`.

**Attack concept:** enlarge the enemy head collider/bone so body shots near the
neck/upper chest register as headshots. A dynamic scale toggle after the first
shot could produce the reported pattern.

**What must be true for it to work live:** the hit registration must use the
client-side collider, or the server must accept the scaled hit. If the server
uses its own fixed hitbox, this fails.

**Confidence:** high that the surface exists; medium for normal modes (may be
mode-gated or server-validated); high relevance for UGC/custom rooms.

---

### Vector D — UGC custom hitboxes / aim-assist entities

**Confirmed client surface:**

- `UGCSkeletonCustomHitBox.ApplyCustomBoxRecursively(3)`,
  `GetHitBoxChild(2)`, `EnableCustomHitBox(3)` -> `CapsuleCollider`.
- `UGCResBodyPartDef.LoadFromData(bool)`; `message.JDGLHIMBCAF`.
- `UGCAimAssistEntityRepItem.AimAssistDistance` (`float`) and
  `AimAssistCenterOffset` (`Vector3`) with public setters.
- `UGCAimAssistEntity`: `GetAttackableCenterWS()`, `GetHitDamagePos()`,
  `set_LockedAimingCollider(Collider)`, `CanAssistByUGC(bool)`,
  `TakeDamage(4)`.
- `HitDetectColliderHelper.IsUGCAimAssistPart()`.
- `UGCLocalColliderIntegrityValidator.Validate(2)`;
  `ColliderCommon SHA1 mismatch`;
  `UGC game loading: Local ColliderCommon integrity check failed, ...
  EnableLocalColliderAntiHack: ...`.
- `GameVarDef.EnableLocalColliderValidation`,
  `GameVarDef.EnableLocalColliderAntiHack`.

**Attack concept:** a malicious UGC map defines a body part as head, places an
aim-assist entity at the head with a large distance, or enlarges the head bone.
The local SHA1 validator is the mitigation; the config flag may disable it.

**What must be true for it to work live:** the UGC map must pass server
validation, or the client must bypass the local integrity check.

**Confidence:** high for UGC/custom rooms; lower for official maps.

---

### Vector E — iFix runtime patching

**Confirmed client surface:**

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
  `Player.<>iFixBaseProxy_get_CanBeLockedByAimAssist` — the game itself
  iFix-patches these methods.
- `assembly-csharp-patch` is an encrypted UnityFS bundle
  (`key_sig=b'd442e25cd401db5b'`,
  `data_sig=b'\x00\x00\x00\x04CAB-fb083c06'`); the key was not recovered.
- No signature/verification method is visible in the iFix metadata. The loader
  accepts a file path or stream.

**Attack concept:** load a custom iFix patch (or replace the patch bundle) to
modify `SetAimRotation`, `GetHeuristicTarget`, `TakeDamage`, `IsPlayerHead`,
`CanBeLockedByAimAssist`, etc. at runtime.

**Why it matters:** this explains persistence across server-side code updates.
It is an enabler for A/B/C, not a headshot mechanic by itself.

**What must be true for it to work live:** the loader must be reachable and
must not verify patch authenticity. If it is signed/verified, this is
mitigated.

**Confidence:** high that the loader exists and is unauthenticated in metadata;
medium that a modded client can reach it.

---

### Vector F — Config / debug-variable tampering

**Confirmed client surface:**

- `SettingDetail`: `aim_assist` (`int`), `aux_aim_sensitivity` (`float`),
  `use_auxaim` (`int`), `use_auxaim_parachute/dash/drive`.
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

**Attack concept:** if active in release, set snap range, soft-assist strength,
head damage ratio, or extra hitbox size via config/memory. `extra_hitbox_*` is
especially interesting: an extra hitbox with a large size and head damage ratio
could directly produce headshots.

**What must be true for it to work live:** the config must be client-readable
and client-authoritative, and the server must not override it.

**Confidence:** high that the fields exist; medium that they are active and
client-authoritative.

---

## 5. Feasibility matrix

| Vector | Client surface | Server dependency | Expected pattern | Static confidence | Dynamic test |
|---|---|---|---|---|---|
| A. Aim-assist lock / aim rotation | Head collider/bone, aim setters, lockable collider | Accepts shot direction / aim delta | First body, then head | High | QA-02, QA-03 |
| B. Hit-collider type spoof | `ColliderInfo.m_hitBoxType`, `EHGMCNBHNMD`, `HNLIMBLIANL` | Trusts client hit part | First body, then head (if delayed) or all head | High | QA-04, QA-05 |
| C. Big-head / bone scale | `BigHeadComponent`, `BodyPartUtilByName` | Client-side hit collider or accepts scaled hit | Body shots become head | High | QA-06 |
| D. UGC custom hitboxes | `UGCSkeletonCustomHitBox`, `UGCAimAssistEntity` | UGC validation / server hitbox | Map-dependent | High (UGC) | QA-07 |
| E. iFix patch | `PatchManager.Load`, `InjectFixManager.LoadPatch` | Patch authenticity | Enables A/B/C | High | QA-08 |
| F. Config/debug tampering | `DebugWeaponAimAssist*`, `extra_hitbox_*` | Config authority | Strengthens A/B | Medium | QA-09 |

---

## 6. Which vector best explains the reported pattern?

| Vector | Match | Reasoning |
|---|---|---|
| A. Aim-assist lock / aim rotation | **Best** | First shot acquires the body target; then the lock moves to the head for subsequent shots. |
| B. Hit-collider-type spoof | **Strong** | Body collider relabeled as `Head`; a delayed toggle after the first hit explains the first body shot. |
| C. Big-head / bone scaling | **Possible** | Head collider enlarged after the first shot; body shots near the head register as headshots. |
| D. UGC custom hitboxes | **Possible** | Malicious UGC map defines a head hitbox/aim-assist entity; mode-dependent. |
| E. iFix patch | **Enabler** | Patches A/B/C at runtime; explains persistence. |
| F. Config tampering | **Enabler** | Strengthens aim assist / head damage; needs release activation. |

The most likely stack is **A + E**: a client-side aim-assist/aimbot that locks
onto the head, delivered/persisted through iFix. **B** is the most likely
alternative if the server trusts the client’s body part. **C** is the most
likely “other vector” for a direct headshot cheat that does not require precise
aim.

---

## 7. QA validation plan

The full plan is in `reports/qa-test-plan.md`. Summary:

| Test | Vector | What it proves |
|---|---|---|
| QA-01 | Baseline | Control: unmodified client, normal hit registration |
| QA-02 | A | Whether aim-assist lock to head produces first-body-then-head |
| QA-03 | A | Whether aim-rotation override to head is accepted |
| QA-04 | B | Whether a body collider reported as `Head` is accepted |
| QA-05 | B | Whether forged damage info with `Head` is accepted |
| QA-06 | C | Whether scaled head collider changes hit registration |
| QA-07 | D | Whether a private UGC map can define a head hitbox/aim-assist entity |
| QA-08 | E | Whether an unsigned iFix patch is accepted |
| QA-09 | F | Whether debug/config tampering changes aim assist in release-like build |
| QA-10 | Detection | Whether telemetry captures the above and triggers enforcement |

**Environment:** private test server, two test accounts, instrumented test
client built by the security team, packet capture, server logs, screen
recording. **No production, no real players, written authorization required.**

**Proof standard:** a vector is “live-practical” only if the server accepts the
resulting hit/damage in repeated trials and the behavior matches the reported
pattern. If the server rejects it, the vector is mitigated for that build.

---

## 8. Detection and mitigation recommendations

1. **Server-authoritative hit resolution.** Recompute the hit collider/body
   part from the client’s shot origin/direction against server-side hitboxes.
   Do not accept client `EHITBODYPART`/`EHGMCNBHNMD` at face value.
2. **Validate aim deltas and fire cadence.** Flag impossible snap angles,
   repeated head-only hits after a body hit, and abnormal
   `SetAimRotation`/`CallSetAimRotationCount` patterns.
3. **Harden aim assist.** Do not expose `set_LockedAimingCollider` to arbitrary
   colliders; clamp `SightAimAssistSnapRange`, soft-assist strength, and
   distance-priority values server-side; ignore client-side debug vars.
4. **Big-head / bone-scale validation.** If big-head is a mode feature, enforce
   `EnableBigHead` and the scale value server-side; validate the head collider
   size used for hit resolution.
5. **UGC collider integrity.** Keep `EnableLocalColliderAntiHack` enabled and
   verify `ColliderCommon` SHA1 server-side; validate UGC body-part definitions
   and aim-assist entity placement.
6. **iFix patch authenticity.** Sign/verify the `assembly-csharp-patch` bundle
   and any patch loaded via `PatchManager.Load`; reject unsigned patches and
   log patch loads. Restrict `LoadTestPatch` in release builds.
7. **Remove debug knobs from release.** Strip or gate `DebugWeaponAimAssist*`,
   `extra_hitbox_*`, and similar config keys; do not let client config override
   server values.
8. **Telemetry.** Log body part, collider type, shot direction, aim delta, and
   target head/body positions for headshot-heavy sessions; use this to
   distinguish A/B/C.

---

## 9. Decision gates

| Gate | Question | Evidence | Status |
|---|---|---|---|
| G1 | Do the client surfaces exist? | `verify_evidence.py` 32/32 | **PASS** |
| G2 | Does the server accept the aim/hit claim? | QA-02..QA-05 | **PENDING** |
| G3 | Does head scaling affect live hit registration? | QA-06 | **PENDING** |
| G4 | Is the iFix loader unauthenticated? | QA-08 | **PENDING** |
| G5 | Does telemetry detect the behavior? | QA-10 | **PENDING** |
| G6 | Is the exact reported pattern reproducible? | QA-02 + QA-04 + end-to-end | **PENDING** |

Do not move to “confirmed live cheat” until G2 and G6 pass. If G2 fails, the
cheat may still work through a different vector; test B/C before concluding.

---

## Appendix A — Static verifier output (32/32)

```
=== Free Fire MAX 2.133.1 - Static Evidence Verification ===
Metadata: analysis/data/global-metadata.dec.dat
Binary:   extracted/work/config/lib/arm64-v8a/libil2cpp.so
Types:    43956

[PASS] COW.GamePlay.Player (T32128, 1692 fields, 4143 methods)
[PASS] COW.GamePlay.OGKFEMJNCGM (T32214, 0 fields, 22 methods)
[PASS] COW.GamePlay.HitDetectColliderHelper (T34569, 3 fields, 53 methods)
[PASS] .ColliderInfo (T438, 2 fields, 1 methods)
[PASS] .HitPart (T439, 22 fields, 0 methods)
[PASS] COW.GamePlay.EHGMCNBHNMD (T34568, 67 fields, 0 methods)
[PASS] COW.GamePlay.HNLIMBLIANL (T34272, 15 fields, 23 methods)
[PASS] COW.GamePlay.BigHeadComponent (T32146, 4 fields, 9 methods)
[PASS] COW.BigHeadData (T11147, 14 fields, 5 methods)
[PASS] COW.BodyPartUtilByName (T11057, 4 fields, 13 methods)
[PASS] COW.Gameplay.UGC.UGCSkeletonCustomHitBox (T31222, 0 fields, 4 methods)
[PASS] COW.Gameplay.UGC.UGCLocalColliderIntegrityValidator (T31399, 1 fields, 5 methods)
[PASS] COW.UGCAttachmentRepItem (T13096, 80 fields, 57 methods)
[PASS] COW.UGCAimAssistEntityRepItem (T13085, 8 fields, 9 methods)
[PASS] COW.GamePlay.UGCAimAssistEntity (T35663, 4 fields, 32 methods)
[PASS] COW.WeaponGunFeelProfileData (T11882, 123 fields, 10 methods)
[PASS] COW.WeaponAimAssistAutoAbsorbData (T11875, 10 fields, 8 methods)
[PASS] COW.SettingDetail (T23231, 187 fields, 2 methods)
[PASS] COW.GameModeSetting (T12010, 975 fields, 3 methods)
[PASS] COW.GameVarDef (T12013, 5664 fields, 7 methods)
[PASS] COW.GamePlay.PlayerAttributes (T34846, 180 fields, 269 methods)
[PASS] GCommon.InjectFixManager (T36645, 3 fields, 6 methods)
[PASS] IFix.Core.PatchManager (T43247, 2 fields, 11 methods)

Config/string literals:
  [PASS] 'aim_assist'
  [PASS] 'sight_aim_assist'
  [PASS] 'use_auxaim'
  [PASS] 'extra_hitbox_enable'
  [PASS] 'use_snipercollider_whensighting'
  [PASS] 'EnableLocalColliderAntiHack'
  [PASS] 'HeadScale'
  [PASS] 'HeadShotDamageScale'
  [PASS] 'ColliderCommon SHA1 mismatch'

Summary: 32 passed, 0 failed
```

---

## Appendix B — Key type indices

| Index | Type | Why it matters |
|---:|---|---|
| 32128 | `COW.GamePlay.Player` | head/aim/aim-assist/damage methods |
| 34569 | `COW.GamePlay.HitDetectColliderHelper` | `IsPlayerHead`, `ColliderType` |
| 34272 | `COW.GamePlay.HNLIMBLIANL` | damage info; body-part field |
| 34568 | `COW.GamePlay.EHGMCNBHNMD` | `Head`/`Body`/`Limb` enum |
| 438 | `.ColliderInfo` | `m_hitBoxType` (`.HitPart`) |
| 439 | `.HitPart` | `Head`, `Neck`, `Chest`, ... |
| 32214 | `COW.GamePlay.OGKFEMJNCGM` | aim-assist target interface |
| 34606 | `COW.GamePlay.NLIMDENAFNN` | `Player.m_AimAssist` |
| 34612 | `COW.GamePlay.DCIDAEHLHPI` | `GetAimAssistOnSighting` |
| 34614 | `COW.GamePlay.PLOAJDMCLGB` | ice-wall aim assist |
| 11882 | `COW.WeaponGunFeelProfileData` | `strongAimAssistShot`, soft assist |
| 11875 | `COW.WeaponAimAssistAutoAbsorbData` | auto-absorb config |
| 13096 | `COW.UGCAttachmentRepItem` | `SightAimAssist*` setters |
| 13085 | `COW.UGCAimAssistEntityRepItem` | UGC aim-assist distance/offset |
| 35663 | `COW.GamePlay.UGCAimAssistEntity` | UGC aim-assist entity |
| 32146 | `COW.GamePlay.BigHeadComponent` | head collider + `UpdateScale` |
| 11147 | `COW.BigHeadData` | `HeadScale`, `HeadShotDamageScale` |
| 11057 | `COW.BodyPartUtilByName` | head-bone scaling |
| 31222 | `COW.Gameplay.UGC.UGCSkeletonCustomHitBox` | UGC custom hitboxes |
| 31399 | `COW.Gameplay.UGC.UGCLocalColliderIntegrityValidator` | UGC SHA1 check |
| 31407 | `COW.Gameplay.UGC.UGCResBodyPartDef` | UGC body-part defs |
| 23231 | `COW.SettingDetail` | `aim_assist`, `use_auxaim` |
| 12010 | `COW.GameModeSetting` | `BanAimAssist`, `EnableBigHead` |
| 12013 | `COW.GameVarDef` | debug aim-assist / anti-cheat flags |
| 34846 | `COW.GamePlay.PlayerAttributes` | `BuffEcaWeaponAimAssist*` |
| 36645 | `GCommon.InjectFixManager` | iFix patch loader |
| 43247 | `IFix.Core.PatchManager` | `Load(string filepath)` |

---

## Appendix C — Key method signatures

```
Player.get_HeadCollider() -> Collider
Player.get_HeadBoneTransform() -> Transform
Player.GetHeadTF() -> Transform
Player.SetAimRotation(Quaternion, bool) -> void
Player.GetAimRotation() -> Quaternion
Player.GetAuxAimRotation() -> Quaternion
Player.ResetAuxAimRotation() -> void
Player.UpdateAiming(float, float, bool) -> void
Player.GetHeuristicTarget() -> OGKFEMJNCGM
Player.GetHeuristicTargetInfoScore() -> float
Player.SetEAimAssitMode(EAimAssist) -> void
Player.GetAimAssistOnSighting() -> DCIDAEHLHPI
Player.GetAimAssistDampCoefficient(HBIBDMMOOOK) -> float
Player.TakeDamage(HNLIMBLIANL, PIAEKELILCJ, <delegate>, uint) -> void
Player.TakeDamage(int, BEADLMGGGGL, HNLIMBLIANL, int, Vector3, Vector3,
                  <delegate>, PIAEKELILCJ, uint) -> int
OGKFEMJNCGM.GetAttackableCenterWS() -> Vector3
OGKFEMJNCGM.GetHitDamagePos() -> Vector3
OGKFEMJNCGM.get_LockedAimingCollider() -> Collider
OGKFEMJNCGM.set_LockedAimingCollider(Collider) -> void
HitDetectColliderHelper.IsPlayerHead() -> bool
BigHeadComponent.UpdateScale(float) -> void
BodyPartUtilByName.SetBoneDynamicScale(3 params) -> void
UGCSkeletonCustomHitBox.EnableCustomHitBox(3 params) -> CapsuleCollider
GCommon.InjectFixManager.LoadPatch(string patchFileAb) -> void
GCommon.InjectFixManager.LoadTestPatch() -> void
IFix.Core.PatchManager.Load(string filepath) -> VirtualMachine
```

---

## Appendix D — Config keys / literals

```
aim_assist
aim_assist_lock_keep_time
aim_assist_lock_decrease_time
aim_assist_max_screen_range
aim_assist_min_screen_range
aim_assist_specified
can_aimassist
sight_aim_assist
sight_aim_assist_snap_range
sight_aim_assist_dist_falloff
sight_aim_assist_distpriority
sight_aim_assist_distprio_min
sight_aim_assist_distprio_max
sight_aim_assist_distprio_coef
use_auxaim
aux_aim_sensitivity
use_snipercollider_whensighting
extra_hitbox_enable
extra_hitbox_size
extra_hitbox_armor_enable
extra_hitbox_damage_ratio
headshot_min_ratio
headshot_full_ratio_distance
headshot_min_ratio_distance
shield_damge_by_bodypart
```
