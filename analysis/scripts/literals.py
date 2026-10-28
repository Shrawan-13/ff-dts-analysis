import struct,re,sys
d=open('/tmp/global-metadata.dec.dat','rb').read()
H=struct.unpack_from('<60I',d,0)
LO,LS,LD,LDS=H[2],H[3],H[4],H[5]
n=LS//8
lits=[]
for i in range(n):
    ln,di=struct.unpack_from('<Ii',d,LO+i*8)
    if ln<0 or ln>10000: continue
    s=d[LD+di:LD+di+ln].decode('utf-8','replace')
    lits.append(s)
print('literals',len(lits))
pat=re.compile(sys.argv[1] if len(sys.argv)>1 else r'aim|assist|hitbox|body|head|recoil|spread|snap|lock|target|damage|fire|shoot|bullet',re.I)
seen=set()
for s in lits:
    if pat.search(s) and s not in seen:
        seen.add(s); print(repr(s))
