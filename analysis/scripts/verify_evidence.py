#!/usr/bin/env python3
"""Reproduce the static evidence behind the Free Fire MAX 2.133.1 report.

This script checks that the clean APK's decrypted IL2CPP metadata actually
contains the types, fields, methods, and config strings cited in the report.
It is a *static evidence verifier*, not a cheat and not a dynamic exploit.

Usage:
    python3 verify_evidence.py
    python3 verify_evidence.py --json
    FF_META=/path/to/global-metadata.dec.dat python3 verify_evidence.py

If `libil2cpp.so` and `pyelftools` are available, field types are resolved
through the relocated Il2CppType table (same logic as dump_type_resolved.py).
Otherwise the script falls back to presence checks only.
"""
import argparse
import json
import os
import struct
import sys

DEFAULT_META = "/home/shrawan/experiments/hackathon/analysis/data/global-metadata.dec.dat"
DEFAULT_BIN = "/home/shrawan/experiments/hackathon/extracted/work/config/lib/arm64-v8a/libil2cpp.so"


class Metadata:
    def __init__(self, path):
        self.data = open(path, "rb").read()
        self.H = struct.unpack_from("<60I", self.data, 0)
        self.string_base = self.H[6]
        self.type_def_offset = self.H[40]
        self.type_def_count = self.H[41] // 88
        self.field_offset = self.H[24]
        self.method_offset = self.H[12]
        self.literal_offset = self.H[2]
        self.literal_size = self.H[3]
        self.literal_data_offset = self.H[4]
        self.literal_data_size = self.H[5]

    def string(self, index):
        end = self.data.index(b"\0", self.string_base + index)
        return self.data[self.string_base + index:end].decode("utf-8", "replace")

    def type_def(self, index):
        v = struct.unpack_from("<16I8H2I", self.data, self.type_def_offset + index * 88)
        return {
            "name": self.string(v[0]),
            "namespace": self.string(v[1]),
            "field_start": v[8],
            "method_start": v[9],
            "method_count": v[16],
            "field_count": v[18],
        }

    def field(self, index):
        v = struct.unpack_from("<3I", self.data, self.field_offset + index * 12)
        return {"name": self.string(v[0]), "type_index": v[1], "token": v[2]}

    def method(self, index):
        v = struct.unpack_from("<10I", self.data, self.method_offset + index * 40)
        return {
            "name": self.string(v[0]),
            "declaring_type": v[1],
            "return_type": v[2],
            "parameter_start": v[4],
            "parameter_count": v[9] >> 16,
            "raw": v,
        }

    def type_map(self):
        result = {}
        for i in range(self.type_def_count):
            t = self.type_def(i)
            result[t["namespace"] + "." + t["name"]] = (i, t)
        return result

    def fields_of(self, index):
        t = self.type_def(index)
        return [self.field(t["field_start"] + j) for j in range(t["field_count"])]

    def methods_of(self, index):
        t = self.type_def(index)
        return [self.method(t["method_start"] + j) for j in range(t["method_count"])]

    def literals(self):
        result = set()
        count = self.literal_size // 8
        for i in range(count):
            length, data_index = struct.unpack_from("<Ii", self.data, self.literal_offset + i * 8)
            if length < 0 or length > 20000:
                continue
            start = self.literal_data_offset + data_index
            end = start + length
            if end > len(self.data):
                continue
            try:
                result.add(self.data[start:end].decode("utf-8"))
            except UnicodeDecodeError:
                continue
        return result


def load_type_resolver(binary_path):
    """Return a function that resolves an Il2CppType index to a name, or None."""
    if not binary_path or not os.path.exists(binary_path):
        return None
    try:
        import dump_type_resolved as d
    except Exception:
        return None
    try:
        return d.resolve
    except Exception:
        return None


CHECKS = [
    {
        "type": "COW.GamePlay.Player",
        "methods": [
            "get_HeadCollider", "get_HeadBoneTransform", "GetHeadTF",
            "SetAimRotation", "GetAimRotation", "GetAuxAimRotation",
            "ResetAuxAimRotation", "UpdateAiming", "GetHeuristicTarget",
            "GetHeuristicTargetInfoScore", "SetEAimAssitMode",
            "GetAimAssistOnSighting", "GetAimAssistDampCoefficient",
            "IsNeedAimAssists", "get_CanBeLockedByAimAssist",
            "get_IsBanAimAssistState", "TakeDamage", "IsInNoHeadShotState",
            "GetBigHeadScale", "IsInBigHeadScale",
        ],
        "fields": [
            "m_CurrentAimRotation", "CallSetAimRotationCount",
            "m_AimAssist", "m_AimAssistForIceWall",
        ],
    },
    {
        "type": "COW.GamePlay.OGKFEMJNCGM",
        "methods": [
            "get_LockedAimingCollider", "set_LockedAimingCollider",
            "GetAttackableCenterWS", "GetHitDamagePos", "NeedAssit",
            "CanAssitByWeapon", "get_CanBeLockedByAimAssist",
        ],
    },
    {
        "type": "COW.GamePlay.HitDetectColliderHelper",
        "methods": ["IsPlayerHead", "IsUGCAimAssistPart"],
    },
    {
        "type": ".ColliderInfo",
        "fields": ["m_collider", "m_hitBoxType"],
        "field_types": {"m_hitBoxType": ".HitPart"},
    },
    {
        "type": ".HitPart",
        "fields": ["Head", "Neck", "Chest", "Hips"],
    },
    {
        "type": "COW.GamePlay.EHGMCNBHNMD",
        "fields": ["Head", "Body", "Limb", "UGCAimAssistPart"],
    },
    {
        "type": "COW.GamePlay.HNLIMBLIANL",
        "fields": ["BGMOAOCFPGM", "BIHCFIINIBK"],
        "field_types": {"BGMOAOCFPGM": "COW.GamePlay.EHGMCNBHNMD"},
    },
    {
        "type": "COW.GamePlay.BigHeadComponent",
        "methods": ["get_scaleValue", "UpdateScale", "SetNeckRevertScaleMult"],
        "fields": ["GFCGPPKLKEP", "OLAPDAPHKIE"],
        "field_types": {"GFCGPPKLKEP": "UnityEngine.CapsuleCollider"},
    },
    {
        "type": "COW.BigHeadData",
        "fields": ["HeadScale", "HeadShotDamageScale"],
    },
    {
        "type": "COW.BodyPartUtilByName",
        "methods": ["SetBoneDynamicScale", "AddOrUpdateBoneScale", "setAllBoneScale"],
    },
    {
        "type": "COW.Gameplay.UGC.UGCSkeletonCustomHitBox",
        "methods": ["EnableCustomHitBox", "ApplyCustomBoxRecursively", "GetHitBoxChild"],
    },
    {
        "type": "COW.Gameplay.UGC.UGCLocalColliderIntegrityValidator",
        "methods": ["Validate", "ValidateFiles"],
    },
    {
        "type": "COW.UGCAttachmentRepItem",
        "methods": [
            "get_SightAimAssist", "set_SightAimAssist",
            "get_SightAimAssistSnapRange", "set_SightAimAssistSnapRange",
            "get_SightAimAssistDistFalloff", "set_SightAimAssistDistFalloff",
            "get_SightAimAssistDistpriority", "set_SightAimAssistDistpriority",
        ],
    },
    {
        "type": "COW.UGCAimAssistEntityRepItem",
        "methods": [
            "get_AimAssistDistance", "set_AimAssistDistance",
            "get_AimAssistCenterOffset", "set_AimAssistCenterOffset",
        ],
    },
    {
        "type": "COW.GamePlay.UGCAimAssistEntity",
        "methods": [
            "GetAttackableCenterWS", "GetHitDamagePos",
            "set_LockedAimingCollider", "CanAssistByUGC",
        ],
    },
    {
        "type": "COW.WeaponGunFeelProfileData",
        "fields": [
            "strongAimAssistShot", "enableSoftAssist",
            "softAssistTargetKeepTime", "softAssistSequentialSmoothingTime",
            "adsSoftAssistMaxYawPerShot", "hipSoftAssistMaxPitchPerShot",
        ],
    },
    {
        "type": "COW.WeaponAimAssistAutoAbsorbData",
        "fields": ["auto_type", "max_range", "max_count", "max_distance"],
    },
    {
        "type": "COW.SettingDetail",
        "fields": ["aim_assist", "use_auxaim", "aux_aim_sensitivity"],
    },
    {
        "type": "COW.GameModeSetting",
        "fields": ["BanAimAssist", "EnableBigHead", "EnableFireColliderScale",
                   "AimAssistKnockDownParam"],
    },
    {
        "type": "COW.GameVarDef",
        "fields": [
            "DebugWeaponAimAssistMaxScore", "DebugWeaponAimAssistMinScore",
            "DebugWeaponAimAssistDampCoefficient",
            "DebugWeaponAimAssistDampYSensitivity",
            "NoHeadshotTimeAfterPoseSwitch", "UseSniperCollider",
            "EnableLocalColliderAntiHack",
        ],
    },
    {
        "type": "COW.GamePlay.PlayerAttributes",
        "fields": [
            "BuffEcaWeaponAimAssist", "BuffEcaWeaponAimAssistScreenRangeScale",
            "BuffEcaWeaponAimAssistLockDecreaseTimeScale",
            "BuffEcaWeaponAimAssistLockDecreaseTimeSightScale",
        ],
    },
    {
        "type": "GCommon.InjectFixManager",
        "methods": ["LoadPatch", "LoadTestPatch", "Support"],
    },
    {
        "type": "IFix.Core.PatchManager",
        "methods": ["Load"],
    },
]

LITERALS = [
    "aim_assist",
    "sight_aim_assist",
    "use_auxaim",
    "extra_hitbox_enable",
    "use_snipercollider_whensighting",
    "EnableLocalColliderAntiHack",
    "HeadScale",
    "HeadShotDamageScale",
    "ColliderCommon SHA1 mismatch",
]


def run(meta_path, bin_path):
    md = Metadata(meta_path)
    types = md.type_map()
    resolve = load_type_resolver(bin_path)

    results = []
    passed = 0
    failed = 0

    for check in CHECKS:
        name = check["type"]
        entry = types.get(name)
        if entry is None:
            results.append({"type": name, "ok": False, "error": "type not found"})
            failed += 1
            continue

        index, tdef = entry
        fields = {f["name"]: f for f in md.fields_of(index)}
        methods = {m["name"]: m for m in md.methods_of(index)}
        missing_fields = [n for n in check.get("fields", []) if n not in fields]
        missing_methods = [n for n in check.get("methods", []) if n not in methods]

        type_errors = []
        if resolve:
            for field_name, expected in check.get("field_types", {}).items():
                f = fields.get(field_name)
                if f is None:
                    type_errors.append(f"{field_name}: field missing")
                    continue
                actual = resolve(f["type_index"])
                if actual != expected:
                    type_errors.append(f"{field_name}: expected {expected}, got {actual}")

        ok = not missing_fields and not missing_methods and not type_errors
        if ok:
            passed += 1
        else:
            failed += 1
        results.append({
            "type": name,
            "index": index,
            "ok": ok,
            "missing_fields": missing_fields,
            "missing_methods": missing_methods,
            "type_errors": type_errors,
            "field_count": tdef["field_count"],
            "method_count": tdef["method_count"],
        })

    literals = md.literals()
    literal_results = []
    for text in LITERALS:
        ok = any(text in s for s in literals)
        if ok:
            passed += 1
        else:
            failed += 1
        literal_results.append({"literal": text, "ok": ok})

    return {
        "metadata": meta_path,
        "binary": bin_path,
        "type_count": md.type_def_count,
        "checks": results,
        "literals": literal_results,
        "passed": passed,
        "failed": failed,
    }


def print_text(report):
    print("=== Free Fire MAX 2.133.1 - Static Evidence Verification ===")
    print(f"Metadata: {report['metadata']}")
    print(f"Binary:   {report['binary']}")
    print(f"Types:    {report['type_count']}")
    print()
    for r in report["checks"]:
        if r.get("error"):
            print(f"[FAIL] {r['type']}: {r['error']}")
            continue
        status = "PASS" if r["ok"] else "FAIL"
        print(f"[{status}] {r['type']} (T{r['index']}, "
              f"{r['field_count']} fields, {r['method_count']} methods)")
        for n in r.get("missing_fields", []):
            print(f"       missing field: {n}")
        for n in r.get("missing_methods", []):
            print(f"       missing method: {n}")
        for e in r.get("type_errors", []):
            print(f"       type mismatch: {e}")
    print()
    print("Config/string literals:")
    for r in report["literals"]:
        print(f"  [{'PASS' if r['ok'] else 'FAIL'}] {r['literal']!r}")
    print()
    print(f"Summary: {report['passed']} passed, {report['failed']} failed")
    return 0 if report["failed"] == 0 else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--meta", default=os.environ.get("FF_META", DEFAULT_META))
    parser.add_argument("--bin", default=os.environ.get("FF_BIN", DEFAULT_BIN))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run(args.meta, args.bin)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if report["failed"] == 0 else 1
    return print_text(report)


if __name__ == "__main__":
    sys.exit(main())
