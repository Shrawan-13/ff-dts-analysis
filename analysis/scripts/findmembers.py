import struct,re,sys
d=open('/tmp/global-metadata.dec.dat','rb').read()
H=struct.unpack_from('<60I',d,0)
h=dict(zip(['sanity','version','stringLiteralOffset','stringLiteralSize','stringLiteralDataOffset','stringLiteralDataSize','stringOffset','stringSize','eventsOffset','eventsSize','propertiesOffset','propertiesSize','methodsOffset','methodsSize','parameterDefaultValuesOffset','parameterDefaultValuesSize','fieldDefaultValuesOffset','fieldDefaultValuesSize','fieldAndParameterDefaultValueDataOffset','fieldAndParameterDefaultValueDataSize','fieldMarshaledSizesOffset','fieldMarshaledSizesSize','parametersOffset','parametersSize','fieldsOffset','fieldsSize','genericParametersOffset','genericParametersSize','genericParameterConstraintsOffset','genericParameterConstraintsSize','genericContainersOffset','genericContainersSize','nestedTypesOffset','nestedTypesSize','interfacesOffset','interfacesSize','vtableMethodsOffset','vtableMethodsSize','interfaceOffsetsOffset','interfaceOffsetsSize','typeDefinitionsOffset','typeDefinitionsSize','imagesOffset','imagesSize','assembliesOffset','assembliesSize','fieldRefsOffset','fieldRefsSize','referencedAssembliesOffset','referencedAssembliesSize','attributeDataOffset','attributeDataSize','attributeDataRangeOffset','attributeDataRangeSize','unresolvedVirtualCallParameterTypesOffset','unresolvedVirtualCallParameterTypesSize','unresolvedVirtualCallParameterRangesOffset','unresolvedVirtualCallParameterRangesSize','windowsRuntimeTypeNamesOffset','windowsRuntimeTypeNamesSize'],H))
S=h['stringOffset']
def s(i):
    e=d.index(b'\0',S+i); return d[S+i:e].decode('utf-8','replace')
T=h['typeDefinitionsOffset']; NT=h['typeDefinitionsSize']//88
M=h['methodsOffset']; NM=h['methodsSize']//40
F=h['fieldsOffset']; NF=h['fieldsSize']//12
P=h['parametersOffset']; NP=h['parametersSize']//12
def typ(i):
    v=struct.unpack_from('<16I8H2I',d,T+i*88)
    return dict(name=s(v[0]),ns=s(v[1]),fieldStart=v[8],methodStart=v[9],method_count=v[16],field_count=v[18],nested_count=v[20])
types=[typ(i) for i in range(NT)]
def fld(i):
    v=struct.unpack_from('<3I',d,F+i*12); return s(v[0]),v[1],v[2]
def mth(i):
    v=struct.unpack_from('<10I',d,M+i*40); return dict(name=s(v[0]),decl=v[1],ret=v[2],paramStart=v[4],pcount=v[9],flags=v[7],slot=v[8],token=v[6])
methods=[mth(i) for i in range(NM)]
# map fields to types
def members(ti):
    t=types[ti]
    fs=[fld(t['fieldStart']+j) for j in range(t['field_count'])]
    ms=[methods[t['methodStart']+j] for j in range(t['method_count'])]
    return fs,ms
pats=[re.compile(p,re.I) for p in sys.argv[1:]] or [re.compile(r'aim|hitbox|bodypart|head|recoil|spread|bullet|damage',re.I)]
seen=set()
for i,t in enumerate(types):
    fs,ms=members(i)
    hitf=[f for f in fs if any(p.search(f[0]) for p in pats)]
    hitm=[m for m in ms if any(p.search(m['name']) for p in pats)]
    if hitf or hitm:
        key=(t['ns'],t['name'])
        if key in seen: continue
        seen.add(key)
        print(f"\n### T{i} {t['ns']}.{t['name']}  (fields={t['field_count']} methods={t['method_count']})")
        for f in hitf: print(f"  F {f[0]} typeIdx={f[1]}")
        for m in hitm: print(f"  M {m['name']} decl={m['decl']} ret={m['ret']} params={m['pcount']} slot={m['slot']}")
