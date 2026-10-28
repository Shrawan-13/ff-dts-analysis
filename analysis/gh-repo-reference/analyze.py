import json, re, sys, os
outdir = sys.argv[1]
dump_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(outdir, 'dump.cs')
script = json.load(open(os.path.join(outdir, 'script.json')))
strings = json.load(open(os.path.join(outdir, 'stringliteral.json')))

KW = re.compile(r'aim|auxaim|hitbox|hit_box|bodypart|body_part|headshot|head_shot|recoil|spread|bullet|ballistic|shoot|fire|damage|sight|armor|penetrat|weapon', re.I)
KEY_STR = re.compile(r'sight_aim_assist|auxaim|aim_assist|hitbox|hit_box|bodypart|body_part|head|recoil|spread|bullet|damage|shoot|fire', re.I)

def sig(m):
    return f"{m.get('TypeSignature','')} {m.get('Name','')} {m.get('Signature','')}"

methods = script.get('ScriptMethod', [])
hits = [m for m in methods if KW.search(m.get('Name',''))]
# De-dupe and sort by name
seen=set(); uniq=[]
for m in hits:
    k=(m.get('Name'),m.get('Address'))
    if k in seen: continue
    seen.add(k); uniq.append(m)
uniq.sort(key=lambda m: m.get('Name',''))

print('# IL2CPP client analysis\n')
print('Input: Free Fire MAX 2.133.1 (com.dts.freefiremax), libil2cpp.so + global-metadata.dat\n')
print('## 1. Relevant native methods\n')
print('| RVA | Method | Signature |')
print('|---|---|---|')
for m in uniq[:2000]:
    print(f"| 0x{m.get('Address',0):X} | `{m.get('Name','')}` | `{m.get('Signature','')}` |")

print('\n## 2. Relevant string literals\n')
sl = [s for s in strings if KEY_STR.search(s.get('value',''))]
sl.sort(key=lambda s: s.get('value',''))
for s in sl[:500]:
    print(f"- `{s.get('address')}`  `{s.get('value')}`")

print('\n## 3. Class excerpts\n')
# Parse dump.cs class blocks by brace matching, then filter members.
text = open(dump_path, encoding='utf-8', errors='replace').read()
lines = text.splitlines()
class_re = re.compile(r'^\s*(?:public|private|protected|internal)?\s*(?:sealed\s+|abstract\s+|static\s+|partial\s+)*class\s+([A-Za-z0-9_<>`]+)')
targets = ['Player', 'GameSettingData', 'WeaponGunFeelProfileData', 'WeaponGunFeelTuningData',
           'WeaponPropertyUtil', 'UIHudAuxAimController', 'UIHudAuxFireController',
           'UIHudFireController', 'CameraControllerBase', 'SettingDetail', 'GameVarDef',
           'UGCSkeletonCustomHitBox', 'UGCSkeletonAvatarSystem', 'ColliderInfo',
           'MatchModelKillData', 'GameModeSetting']
for i, line in enumerate(lines):
    m = class_re.match(line)
    if not m or m.group(1) not in targets:
        continue
    # collect until braces balance
    depth = 0; started = False; block = []
    for j in range(i, min(len(lines), i+20000)):
        l = lines[j]
        block.append(l)
        depth += l.count('{') - l.count('}')
        if '{' in l: started = True
        if started and depth <= 0:
            break
    print(f"\n### `{m.group(1)}`\n")
    for l in block:
        if re.search(r'class |// RVA|public |private |protected |internal |=>|;', l) and KW.search(l):
            print(l)
        elif re.match(r'^\s*(public|private|protected|internal)\s+.*\b(class|struct|enum)\b', l):
            print(l)
