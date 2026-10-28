import struct,sys
d=open('/tmp/global-metadata.dec.dat','rb').read()
H=struct.unpack_from('<60I',d,0)
h=dict(zip(['sanity','version','stringLiteralOffset','stringLiteralSize','stringLiteralDataOffset','stringLiteralDataSize','stringOffset','stringSize','eventsOffset','eventsSize','propertiesOffset','propertiesSize','methodsOffset','methodsSize','parameterDefaultValuesOffset','parameterDefaultValuesSize','fieldDefaultValuesOffset','fieldDefaultValuesSize','fieldAndParameterDefaultValueDataOffset','fieldAndParameterDefaultValueDataSize','fieldMarshaledSizesOffset','fieldMarshaledSizesSize','parametersOffset','parametersSize','fieldsOffset','fieldsSize','genericParametersOffset','genericParametersSize','genericParameterConstraintsOffset','genericParameterConstraintsSize','genericContainersOffset','genericContainersSize','nestedTypesOffset','nestedTypesSize','interfacesOffset','interfacesSize','vtableMethodsOffset','vtableMethodsSize','interfaceOffsetsOffset','interfaceOffsetsSize','typeDefinitionsOffset','typeDefinitionsSize','imagesOffset','imagesSize','assembliesOffset','assembliesSize','fieldRefsOffset','fieldRefsSize','referencedAssembliesOffset','referencedAssembliesSize','attributeDataOffset','attributeDataSize','attributeDataRangeOffset','attributeDataRangeSize','unresolvedVirtualCallParameterTypesOffset','unresolvedVirtualCallParameterTypesSize','unresolvedVirtualCallParameterRangesOffset','unresolvedVirtualCallParameterRangesSize','windowsRuntimeTypeNamesOffset','windowsRuntimeTypeNamesSize'],H))
S=h['stringOffset']; T=h['typeDefinitionsOffset']; M=h['methodsOffset']; F=h['fieldsOffset']
def s(i):
    e=d.index(b'\0',S+i); return d[S+i:e].decode('utf-8','replace')
def typ(i):
    v=struct.unpack_from('<16I8H2I',d,T+i*88)
    return dict(name=s(v[0]),ns=s(v[1]),fieldStart=v[8],methodStart=v[9],method_count=v[16],field_count=v[18])
def fld(i):
    v=struct.unpack_from('<3I',d,F+i*12); return s(v[0]),v[1],v[2]
def mth(i):
    v=struct.unpack_from('<10I',d,M+i*40); return dict(name=s(v[0]),decl=v[1],ret=v[2])
for arg in sys.argv[1:]:
    i=int(arg)
    t=typ(i); print(f"\n### T{i} {t['ns']}.{t['name']} fields={t['field_count']} methods={t['method_count']}")
    for j in range(t['field_count']):
        n,ti,tok=fld(t['fieldStart']+j); print(f"  F {n} typeIdx={ti} token=0x{tok:08X}")
    for j in range(t['method_count']):
        m=mth(t['methodStart']+j); print(f"  M {m['name']} ret={m['ret']}")
