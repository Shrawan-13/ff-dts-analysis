# Free Fire MAX 2.133.1 — Client-Side Headshot Cheat Analysis (Draft)

**Scope:** clean official XAPK (`com.dts.freefiremax`, version `2.133.1`,
versionCode `2019118527`, Unity IL2CPP). The cheat itself is not present in the
APK; this report identifies the client surfaces a cheat would abuse and assesses
which one best explains the reported pattern:

> first bullet hits body, subsequent bullets hit head while holding fire

**Status:** metadata-level analysis complete; server-trust confirmation pending.
The binary is protected, so static code dumping is unreliable. All findings
below come from the intact IL2CPP metadata plus the relocated `Il2CppType` table
in `libil2cpp.so`.

---

## 1. Executive summary

The game exposes everything a client-side headshot cheat needs:

1. **Direct head references** — `Player.get_HeadCollider()`,
   `Player.get_HeadBoneTransform()`, `Player.GetHeadTF()`.
2. **Aim write primitives** — `Player.SetAimRotation(Quaternion, bool)`,
   `Player.m_CurrentAimRotation`, `Player.UpdateAiming(float, float, bool)`,
   `Player.GetAuxAimRotation()`, `Player.ResetAuxAimRotation()`.
3. **Aim-assist target control** — `Player.GetHeuristicTarget()` returns
   `OGKFEMJNCGM`, which has `get/set_LockedAimingCollider(Collider)`,
   `GetAttackableCenterWS()`, `GetHitDamagePos()`, and
   `get_CanBeLockedByAimAssist()`.
4. **Hit-part data** — `ColliderInfo.m_hitBoxType` is a `HitPart`
   (`Head`, `Neck`, `Chest`, ...), and `HitDetectColliderHelper.IsPlayerHead()`
   exists. Damage info (`HNLIMBLIANL`) carries `EHGMCNBHNMD`
   (`Head`, `Body`, `Limb`, ...) into `Player.TakeDamage(...)`.
5. **Head scaling** — `BigHeadComponent` has a head `CapsuleCollider` and
   `UpdateScale(float)`; `BigHeadData.HeadScale` and
   `BodyPartUtilByName.SetBoneDynamicScale(...)` can enlarge the head.
6. **Runtime patching** — iFix (`IFix.Core.PatchManager.Load(string filepath)`,
   `GCommon.InjectFixManager.LoadPatch(...)`) can patch methods at runtime; no
   signature verification is visible in the metadata.

**Best match for the exact pattern:** a client-side **aim/aim-assist override**
that acquires a body target on the first shot, then locks the aim-assist
collider to the target's head for subsequent shots (Vector A).

**Strongest alternative:** **hit-collider-type spoofing** — relabel a body
collider as `Head`, or force `IsPlayerHead()` true, so body hits are reported as
headshots (Vector B).

**Other direct headshot vectors:** big-head / head-bone scaling (Vector C),
UGC custom hitboxes and UGC aim-assist entities (Vector D), iFix runtime
patches (Vector E), and config/debug-variable tampering (Vector F).

The client-side surfaces are confirmed. Whether each one succeeds depends on
server validation of the shot direction, hit collider, and body part — that is
the main open question.

---

## 2. Methodology (why the metadata is trustworthy)

The XAPK contains Unity IL2CPP:

- `libil2cpp.so` (187,877,616 bytes) — protected
  (`WARNING: find .init_proc`, `ERROR: This file may be protected`).
- `global-metadata.dat` (57,455,604 bytes) — XOR-encrypted with key `0xE8`;
  decrypted magic `0xFAB11BAF`, version 31.

Il2CppDumper v6.7.46 crashes in `Il2CppExecutor.GetMethodSpecName`
(`System.IndexOutOfRangeException`) and writes only an incomplete ~55 KB
`dump.cs`. The protected binary also makes static method pointers unreliable.

We therefore parse the metadata directly:

- Type definitions: 88-byte stride.
- Methods: **40-byte** stride (not 36).
- Fields: 12-byte stride.
- Parameters: 12-byte stride.
- 43,956 type definitions; 104,251 `Il2CppType` entries.

`Il2CppMetadataRegistration` is at VA `0xa705468` (file offset `0xa6fd468`;
the dumper prints virtual addresses). Its `types` pointer at `MR + 0x38`
resolves to `0xa77a8a8` after applying `R_AARCH64_RELATIVE` relocations. This
lets us resolve every field/method type by index, including obfuscated classes.

Tooling and saved dumps are in `analysis/scripts/` and `analysis/outputs/`.
Key type indices are listed in the appendix.

---

## 3. Findings

### Vector A — Aim-assist lock / aim-rotation override (best match)

**Client surface (confirmed):**

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

`OGKFEMJNCGM` (the aim-assist target) exposes:

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
`COW.EUseAuxAimSetting` has `On`, `Off`.

Weapon-side assist data:

- `WeaponGunFeelProfileData.strongAimAssistShot` (`uint`)
- `enableSoftAssist` (`bool`)
- `softAssistTargetKeepTime`, `softAssistSequentialSmoothingTime`,
  `softAssistInputThreshold`, `softAssistInputAttenuation`,
  `softAssistLostStrengthScale`
- `hipSoftAssist*` / `adsSoftAssist*` curves and angle/strength fields
- `adsSoftAssistMaxYawPerShot`, `hipSoftAssistMaxPitchPerShot`, etc.

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

Config keys present as string literals: `aim_assist`,
`aim_assist_lock_keep_time`, `aim_assist_lock_decrease_time`,
`aim_assist_max_screen_range`, `aim_assist_min_screen_range`,
`aim_assist_specified`, `can_aimassist`, `sight_aim_assist*`, `use_auxaim`,
`aux_aim_sensitivity`.

**How it produces the observed pattern:**

1. First shot: the cheat fires at the current/body aim or waits for target
   acquisition. The target is now known (`GetHeuristicTarget()`).
2. The cheat sets the target's `LockedAimingCollider` to the target's
   `HeadCollider`, or computes a quaternion from the camera/muzzle to
   `HeadBoneTransform`/`GetHeadTF` and calls `SetAimRotation(...)`.
3. Holding fire: soft assist / strong assist keeps the aim on the head; each
   subsequent shot is a headshot.

The first-shot body is consistent with target acquisition or a deliberate
one-shot delay. The `CallSetAimRotationCount` field suggests the game may count
`SetAimRotation` calls, so a cheat might write `m_CurrentAimRotation` directly
or use `GetAuxAimRotation`/`UpdateAiming` instead.

**Practicality:** high as a client-side surface. The shot direction is computed
client-side; the server must validate the angle delta and the claimed hit. The
exact pattern is a natural fit for an aimbot with first-shot acquisition.

**Confidence:** high that the surface exists and is usable; medium-high that it
is the exact observed mechanic.

---

### Vector B — Hit-collider-type / body-part spoof (strong alternative)

**Client surface (confirmed):**

- `COW.GamePlay.HitDetectColliderHelper`:
  - `ColliderType` (`EHGMCNBHNMD`)
  - `OCHLCHLHLJC` (`OGKFEMJNCGM`)
  - `MBIDECIOIBM` (`GameObject`)
  - `bool IsPlayerHead()`
  - `bool IsUGCAimAssistPart()`
- `.ColliderInfo`:
  - `m_collider` (`UnityEngine.Collider`)
  - `m_hitBoxType` (`.HitPart`: `Head`, `Neck`, `Chest`, `Hips`, `LeftArm`,
    ... `WeakPoint`)
- `COW.GamePlay.EHGMCNBHNMD`: `None`, `Head`, `Body`, `Limb`, `Vehicle`,
  `Protection`, `UAV`, `Shoal`, `OilDrum`, `IceWall`, `Landmine`, `MiniSentry`,
  `Shield`, `SniperExtension`, `Dummy`, `ShootingTarget`,
  `ShootingTargetHead`, `WeaponShield`, ...
- `COW.GamePlay.HNLIMBLIANL` (damage info) has `BGMOAOCFPGM` of type
  `EHGMCNBHNMD`.
- `Player.TakeDamage` overloads:
  - `void TakeDamage(HNLIMBLIANL, PIAEKELILCJ, <delegate>, uint)`
  - `int TakeDamage(int, BEADLMGGGGL, HNLIMBLIANL, int, Vector3, Vector3,
    <delegate>, PIAEKELILCJ, uint)`
- `message.LPJEFLJOJCM` enum: `EHITBODYPART_NONE`, `EHITBODYPART_HEAD`,
  `EHITBODYPART_BODY`, `EHITBODYPART_LIMB`, `EHITBODYPART_VEHICLE`,
  `EHITBODYPART_PROTECTION`, ...
- `message.MHHELEDEJHG` has a `HitBodyPart` enum value;
  `COW.MatchModelKillData` has `hitBodyPart`.

**How it works:** the client determines the hit collider and its type. A cheat
can:

- change `ColliderInfo.m_hitBoxType` from `Chest`/`Body` to `Head`; or
- set `HitDetectColliderHelper.ColliderType = EHGMCNBHNMD.Head`; or
- force `IsPlayerHead()` to return true; or
- construct a `HNLIMBLIANL` with `BGMOAOCFPGM = Head` and call
  `TakeDamage(...)` on the target.

If the server trusts the client's body part, every body hit becomes a headshot.
The "first body, rest head" pattern could be a delayed toggle after the first
hit (to avoid an immediate anomaly) or a selective relabel of one collider.

**Practicality:** high if the server accepts the client's `EHITBODYPART` /
collider type; medium if the server recomputes the hit from the shot vector.
The client-side `TakeDamage` path and the damage-info body-part field make this
a real attack surface.

**Confidence:** high that the client can spoof the body part; medium that the
server trusts it. This is the first thing to verify with a network trace or a
server-side test.

---

### Vector C — Big-head / head-bone scaling (direct headshot vector)

**Client surface (confirmed):**

- `COW.GamePlay.BigHeadComponent`:
  - `HCMNGNGFCIC` (`float`)
  - `OLAPDAPHKIE` (`UnityEngine.Transform`, head bone)
  - `GFCGPPKLKEP` (`UnityEngine.CapsuleCollider`, head collider)
  - `KHHAACKCJKE` (`UnityEngine.Vector3`)
  - `float get_scaleValue()`
  - `void UpdateScale(float)`
  - `void SetNeckRevertScaleMult(float)`
- `COW.BigHeadData`: `HeadScale`, `HeadShotDamageScale`, `HeadAvatar`,
  `EffectID`, `HeadIcon`, ...
- `Player.IsInBigHeadScale()`, `Player.GetBigHeadScale()`,
  `Player.ApplyBigHeadScalePreHangLateUpdate()`,
  `Player.PlayBigHeadHypeEffect()`, `Player.PlayBigHeadLevelUpEffect()`.
- `COW.BodyPartUtilByName`: `SetBoneDynamicScale(3)`,
  `AddOrUpdateBoneScale(2)`, `setAllBoneScale()`,
  `ControlBoneWorldRotation(2)`.
- UGC: `UGCSkeletonCustomHitBox.EnableCustomHitBox(3)` returns
  `CapsuleCollider`; `UGCPlayerRepItem.HeadBonesScale`;
  `UGCResBodyPartDef.LoadFromData(bool)`.
- `GameModeSetting.EnableBigHead`, `BigHeadCameraBackTriggerScale`,
  `BigHeadCameraBackOffset`.
- String literal: `'BigHeadComponent no find bone_Head gameobject in entity'`.

**How it works:** call `BigHeadComponent.UpdateScale(large)` on enemy players,
or scale the head bone via `BodyPartUtilByName.SetBoneDynamicScale`, so the
head collider becomes much larger. Body shots near the neck/upper chest then
register as headshots. A dynamic scale toggle after the first shot could
produce the observed pattern.

**Practicality:** high for the client-side collider. In normal matches it may
be gated by `EnableBigHead`/server validation; it is especially relevant to
UGC/custom rooms and big-head events.

**Confidence:** high that the surface exists; medium that it works in normal
ranked/BR modes without server checks.

---

### Vector D — UGC custom hitboxes / aim-assist entities

**Client surface (confirmed):**

- `UGCSkeletonCustomHitBox.ApplyCustomBoxRecursively(3)`,
  `GetHitBoxChild(2)`, `EnableCustomHitBox(3)` -> `CapsuleCollider`.
- `UGCResBodyPartDef.LoadFromData(bool)`; `message.JDGLHIMBCAF` data.
- `UGCAimAssistEntityRepItem.AimAssistDistance` (`float`) and
  `AimAssistCenterOffset` (`Vector3`) with public setters.
- `UGCAimAssistEntity`:
  - `GetAttackableCenterWS()`, `GetHitDamagePos()`,
    `set_LockedAimingCollider(Collider)`, `CanAssistByUGC(bool)`,
    `TakeDamage(4)`.
- `HitDetectColliderHelper.IsUGCAimAssistPart()`.
- `UGCLocalColliderIntegrityValidator.Validate(2)`;
  `ColliderCommon SHA1 mismatch`;
  `UGC game loading: Local ColliderCommon integrity check failed, ... EnableLocalColliderAntiHack: ...`.
- `GameVarDef.EnableLocalColliderValidation`,
  `GameVarDef.EnableLocalColliderAntiHack`.

**How it works:** a malicious UGC map can define a body part as head, place an
aim-assist entity at the head with a large `AimAssistDistance`, or enlarge the
head bone. The local SHA1 validator is the mitigation; `EnableLocalColliderAntiHack`
is a config flag a cheat could try to disable.

**Practicality:** high for UGC/custom rooms; lower for official maps unless the
same code paths are reachable. The presence of a local integrity validator
shows the developers are aware of this vector.

**Confidence:** high for UGC; medium for official modes.

---

### Vector E — iFix runtime patching (persistence / bypass)

**Client surface (confirmed):**

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

**How it works:** a cheat can load its own iFix patch (or replace the patch
bundle) to modify `SetAimRotation`, `GetHeuristicTarget`, `TakeDamage`,
`IsPlayerHead`, `CanBeLockedByAimAssist`, etc. at runtime. This explains why
server-side code updates do not remove the cheat.

**Practicality:** high if the loader is reachable and does not verify patch
authenticity. This is a general code-patching vector, not a specific headshot
mechanic, but it is the likely persistence layer.

**Confidence:** high that the loader exists and is unauthenticated in metadata;
medium that a cheat can reach it from a modded client.

---

### Vector F — Config / debug-variable tampering

**Client surface (confirmed):**

- `COW.SettingDetail`: `aim_assist` (`int`), `aux_aim_sensitivity` (`float`),
  `use_auxaim` (`int`), `use_auxaim_parachute/dash/drive`,
  `damage_setting`.
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

**How it works:** if these are active in release, a cheat can set the snap
range, soft-assist strength, head damage ratio, or extra hitbox size via
config/memory. `extra_hitbox_*` is especially interesting: an extra hitbox with
a large size and head damage ratio could directly produce headshots.

**Practicality:** medium — presence in metadata does not prove release
activation or server authority. Worth verifying with a runtime test or a
config-diff.

**Confidence:** high that the fields exist; medium that they are active and
client-authoritative.

---

## 4. Which vector best explains "first body, then head"?

| Vector | Matches pattern | Why |
|---|---|---|
| A. Aim-assist lock / aim rotation | **Best** | First shot acquires body target; then lock to head collider/bone for subsequent shots. |
| B. Hit-collider-type spoof | **Strong** | Body collider relabeled as `Head`; delayed toggle after first hit explains first body shot. |
| C. Big-head / bone scaling | **Possible** | Head collider enlarged after first shot; body shots near the head register as headshots. |
| D. UGC custom hitboxes | **Possible** | Malicious UGC map defines head hitbox/aim-assist entity; mode-dependent. |
| E. iFix patch | **Enabler** | Patches A/B/C at runtime; explains persistence, not the pattern itself. |
| F. Config tampering | **Enabler** | Strengthens aim assist / head damage; needs release activation. |

The most likely stack is **A + E**: a client-side aim-assist/aimbot that locks
onto the head, delivered/persisted through iFix. **B** is the most likely
alternative if the server trusts the client's body part. **C** is the most
likely "other vector" for a direct headshot cheat that does not require precise
aim.

---

## 5. Practicality assessment

- **Client side:** all required primitives are present in the release build:
  head collider/bone, aim rotation setters, aim-assist target/collider control,
  hit-part enums, damage-info construction, head scaling, and a runtime patch
  loader. Nothing needs to be reverse-engineered from scratch; the metadata
  names are readable.
- **Server side:** the critical unknown is validation. If the server:
  - recomputes the hit from the client's shot vector and its own hitboxes, then
    **A** works (the shot vector points at the head) but **B/C** may fail;
  - trusts the client's hit body part/collider type, then **B** works;
  - trusts the client's hit result/damage event, then **B** and direct
    `TakeDamage` calls work;
  - validates the angle delta and fire cadence, then **A** must stay within the
    allowed delta (soft assist / gradual lock can do this).
- **Observed pattern:** "first body, then head" is more consistent with **A**
  (target acquisition then head lock) than with a static **B/C** change, which
  would typically make the first shot a headshot too. A delayed **B/C** toggle
  is possible but less natural.

**Verdict:** the cheat is **practically achievable** from the client side. The
exact implementation cannot be uniquely proven from the clean APK alone, but
the strongest candidate is an aim-assist/aim-rotation override that locks to
the head after the first shot. The strongest alternative is body-part spoofing,
which depends on server trust.

---

## 6. Recommended mitigations

1. **Server-authoritative hit resolution.** Recompute the hit collider/body part
   from the client's shot origin/direction against server-side hitboxes; do not
   accept client `EHITBODYPART`/`EHGMCNBHNMD` at face value.
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
7. **Remove debug knobs from release.** Strip or gate
   `DebugWeaponAimAssist*`, `extra_hitbox_*`, and similar config keys; do not
   let client config override server values.
8. **Telemetry.** Log the body part, collider type, shot direction, aim delta,
   and target head/body positions for headshot-heavy sessions; use this to
   distinguish A/B/C.

---

## 7. Open questions / next work

1. Locate the exact in-match network payload carrying `EHITBODYPART` /
   `EHGMCNBHNMD` and determine whether the server trusts it.
2. Trace callers of `set_LockedAimingCollider` and `SetAimRotation` to confirm
   whether the locked collider feeds the shot ray or only the camera.
3. Test whether `BigHeadComponent.UpdateScale` changes the collider used by
   `HitDetectColliderHelper` on enemies in normal modes.
4. Inspect iFix for signature/hash verification and patch-load call sites.
5. Confirm whether `extra_hitbox_*` and `DebugWeaponAimAssist*` are active in
   release and client-authoritative.

---

## Appendix — key type indices

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
