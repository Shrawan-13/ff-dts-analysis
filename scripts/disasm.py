#!/usr/bin/env python3
"""Disassemble a few high-value IL2CPP methods from a dumped script.json.

The goal is not full decompilation: it is to show which other game methods a
method calls, so a client-side aim/hit path can be verified quickly.
"""
import json
import os
import sys

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile

TARGETS = [
    "GetAuxAimRotation",
    "ResetAuxAimRotation",
    "CheckAuxAimStatusChanged",
    "GetAimAssistOnSighting",
    "GetAimAssistDampCoefficient",
    "IsNeedAimAssists",
    "GetAimRotation",
    "SetAimRotation",
    "UpdateAiming",
    "GetHeuristicTarget",
    "GetHeuristicTargetInfoScore",
    "HasHeuristicTarget",
    "PlayAssistantShot",
    "RequestAssistantShot",
    "GetCameraTrackableEntityAimRotation",
    "GetTargetDirection",
    "RecoilFormula",
    "GetWeaponRecoilProperty",
    "ShouldReplaceAccuracyWithRecoil",
    "TryOverrideHitBox",
    "EnableCustomHitBox",
    "GetHitBoxChild",
    "TakeDamage",
    "CheckDamageFromWeapon",
    "GetHitBodyPart",
    "GetAttackableCenterWS",
    "GetHitDamagePos",
    "SetEAimAssitMode",
    "get_EAimAssit",
]

MAX_BYTES = 0x600


def load_segments(elf_path):
    segs = []
    with open(elf_path, "rb") as f:
        elf = ELFFile(f)
        for seg in elf.iter_segments():
            if seg["p_type"] == "PT_LOAD" and seg["p_filesz"]:
                segs.append((seg["p_vaddr"], seg["p_vaddr"] + seg["p_filesz"], seg["p_offset"]))
    return segs


def rva_to_off(segs, rva):
    for start, end, off in segs:
        if start <= rva < end:
            return off + (rva - start)
    return None


def main():
    outdir = sys.argv[1]
    binary = sys.argv[2]
    script = json.load(open(os.path.join(outdir, "script.json")))
    methods = script.get("ScriptMethod", [])
    # Address -> name for annotating calls.
    by_addr = {}
    for m in methods:
        by_addr.setdefault(int(m.get("Address", 0)), m.get("Name", "?"))
    ordered = sorted((int(m.get("Address", 0)), m.get("Name", "?")) for m in methods)
    addrs = [a for a, _ in ordered]

    segs = load_segments(binary)
    data = open(binary, "rb").read()
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    md.detail = False

    lines = ["# Key method disassembly", ""]
    seen = set()
    for m in methods:
        name = m.get("Name", "")
        if not any(t in name for t in TARGETS):
            continue
        if name in seen:
            continue
        seen.add(name)
        addr = int(m.get("Address", 0))
        off = rva_to_off(segs, addr)
        if off is None:
            lines.append(f"## {name} @ 0x{addr:X}\n\n(could not map RVA)\n")
            continue
        # end at next method or MAX_BYTES
        nxt = None
        lo, hi = 0, len(addrs)
        while lo < hi:
            mid = (lo + hi) // 2
            if addrs[mid] <= addr:
                lo = mid + 1
            else:
                hi = mid
        if lo < len(addrs):
            nxt = addrs[lo]
        size = MAX_BYTES if nxt is None else min(MAX_BYTES, max(16, nxt - addr))
        code = data[off:off + size]
        lines.append(f"## {name} @ 0x{addr:X}")
        lines.append("```")
        for insn in md.disasm(code, addr):
            note = ""
            if insn.mnemonic in ("bl", "b", "br", "blr"):
                try:
                    target = int(insn.op_str, 16)
                except ValueError:
                    target = None
                if target is not None and target in by_addr:
                    note = f"  ; -> {by_addr[target]}"
            lines.append(f"0x{insn.address:X}: {insn.mnemonic:<8} {insn.op_str}{note}")
        lines.append("```")
        lines.append("")

    path = os.path.join(outdir, "disasm.md")
    open(path, "w").write("\n".join(lines))
    print("\n".join(lines[:200]))
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
