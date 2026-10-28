import sys
src, dst = sys.argv[1], sys.argv[2]
d = open(src, 'rb').read()
if d[:4] == b'\xaf\x1b\xb1\xfa':
    out = d
else:
    out = bytes(b ^ 0xE8 for b in d)
if out[:4] != b'\xaf\x1b\xb1\xfa':
    raise SystemExit('not IL2CPP metadata after XOR 0xE8')
open(dst, 'wb').write(out)
print('metadata ok', len(out))
