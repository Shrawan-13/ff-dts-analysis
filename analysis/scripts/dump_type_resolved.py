#!/usr/bin/env python3
"""Dump metadata type definitions with field types resolved from the ELF type table.

This works around Il2CppDumper's failure on the protected Free Fire binary:
the metadata tables are readable, and the Il2CppType table can be resolved by
applying R_AARCH64_RELATIVE relocations from the ELF.
"""
import os
import re
import struct
import sys

from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection

META = os.environ.get("FF_META", "/home/shrawan/experiments/hackathon/analysis/data/global-metadata.dec.dat")
BIN = os.environ.get("FF_BIN", "/home/shrawan/experiments/hackathon/extracted/work/config/lib/arm64-v8a/libil2cpp.so")

md = open(META, "rb").read()
H = struct.unpack_from("<60I", md, 0)
S = H[6]
T = H[40]
NT = H[41] // 88
F = H[24]
M = H[12]

def ms(i):
    e = md.index(b"\0", S + i)
    return md[S + i:e].decode("utf-8", "replace")

def tdef(i):
    v = struct.unpack_from("<16I8H2I", md, T + i * 88)
    return dict(name=ms(v[0]), ns=ms(v[1]), fieldStart=v[8], methodStart=v[9],
                method_count=v[16], field_count=v[18])

def field(i):
    v = struct.unpack_from("<3I", md, F + i * 12)
    return ms(v[0]), v[1], v[2]

def method(i):
    v = struct.unpack_from("<10I", md, M + i * 40)
    return dict(name=ms(v[0]), decl=v[1], ret=v[2], raw=v)

data = open(BIN, "rb").read()
elf = ELFFile(open(BIN, "rb"))
segs = []
for seg in elf.iter_segments():
    if seg["p_type"] == "PT_LOAD" and seg["p_filesz"]:
        segs.append((seg["p_vaddr"], seg["p_vaddr"] + seg["p_filesz"], seg["p_offset"]))

def va2off(va):
    for vs, ve, off in segs:
        if vs <= va < ve:
            return off + (va - vs)
    return None

reloc = {}
for sec in elf.iter_sections():
    if isinstance(sec, RelocationSection):
        for rel in sec.iter_relocations():
            if rel["r_info_type"] == 1027:  # R_AARCH64_RELATIVE
                reloc[rel["r_offset"]] = rel["r_addend"]

def ptr(va):
    if va in reloc:
        return reloc[va]
    off = va2off(va)
    if off is None:
        return None
    return struct.unpack_from("<Q", data, off)[0]

MR = 0xA705468
types_count = struct.unpack_from("<Q", data, va2off(MR + 0x30))[0]
types_ptr = ptr(MR + 0x38)

PRIM = {
    0x01: "void", 0x02: "bool", 0x03: "char", 0x04: "sbyte", 0x05: "byte",
    0x06: "short", 0x07: "ushort", 0x08: "int", 0x09: "uint", 0x0A: "long",
    0x0B: "ulong", 0x0C: "float", 0x0D: "double", 0x0E: "string",
    0x1C: "object", 0x16: "TypedReference", 0x18: "IntPtr", 0x19: "UIntPtr",
}

cache = {}

def type_ptr_name(va, depth=0):
    off = va2off(va)
    if off is None:
        return "?"
    dp, bits = struct.unpack_from("<QI", data, off)
    t = (bits >> 16) & 0xFF
    if t in (0x11, 0x12):
        return tdef(dp)["ns"] + "." + tdef(dp)["name"]
    if t == 0x0E:
        return "string"
    if t == 0x15:
        return resolve_generic(va, depth + 1)
    if t == 0x1D:
        return type_ptr_name(ptr(va) or dp, depth + 1) + "[]"
    if t == 0x0F:
        return type_ptr_name(ptr(va) or dp, depth + 1) + "*"
    return PRIM.get(t, f"type{t:x}")

def resolve_generic(va, depth=0):
    gva = ptr(va)
    if not gva:
        off = va2off(va)
        gva = struct.unpack_from("<Q", data, off)[0] if off else 0
    goff = va2off(gva)
    if goff is None:
        return "?"
    gd = struct.unpack_from("<qQQ", data, goff)
    base = tdef(gd[0])["ns"] + "." + tdef(gd[0])["name"]
    ci = ptr(gva + 8)
    args = []
    if ci:
        cioff = va2off(ci)
        if cioff:
            argc, argv = struct.unpack_from("<QQ", data, cioff)
            for i in range(min(argc, 6)):
                ap = ptr(argv + i * 8)
                if ap:
                    args.append(type_ptr_name(ap, depth + 1))
    return f"{base}<{','.join(args)}>"

def resolve(idx, depth=0):
    if idx in cache:
        return cache[idx]
    if idx >= types_count or depth > 6:
        return f"<bad {idx}>"
    tva = ptr(types_ptr + idx * 8)
    if not tva:
        return f"<null {idx}>"
    off = va2off(tva)
    if off is None:
        return f"<va {tva:x}>"
    dp, bits = struct.unpack_from("<QI", data, off)
    t = (bits >> 16) & 0xFF
    if t in (0x11, 0x12):
        r = tdef(dp)["ns"] + "." + tdef(dp)["name"]
    elif t == 0x0E:
        r = "string"
    elif t == 0x15:
        r = resolve_generic(tva, depth + 1)
    elif t == 0x1D:
        r = type_ptr_name(ptr(tva) or dp, depth + 1) + "[]"
    elif t == 0x0F:
        r = type_ptr_name(ptr(tva) or dp, depth + 1) + "*"
    else:
        r = PRIM.get(t, f"type{t:x}")
    cache[idx] = r
    return r

def dump_type(idx, pat=None):
    t = tdef(idx)
    print(f"\n### T{idx} {t['ns']}.{t['name']}  fields={t['field_count']} methods={t['method_count']}")
    for j in range(t["field_count"]):
        n, ti, tok = field(t["fieldStart"] + j)
        if pat and not pat.search(n):
            continue
        print(f"  F {n:<45} {resolve(ti)}")
    for j in range(t["method_count"]):
        m = method(t["methodStart"] + j)
        if pat and not pat.search(m["name"]):
            continue
        pc = m["raw"][9] >> 16
        print(f"  M {m['name']:<45} ret={resolve(m['ret'])} params={pc}")

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        if ":" in arg:
            idx, pat = arg.split(":", 1)
            dump_type(int(idx), re.compile(pat, re.I))
        else:
            dump_type(int(arg))
