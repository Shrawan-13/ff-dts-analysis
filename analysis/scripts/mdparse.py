import struct, sys, re
p='/tmp/global-metadata.dec.dat'
d=open(p,'rb').read()
H=struct.unpack_from('<60I', d, 0)
names=['sanity','version','stringLiteralOffset','stringLiteralSize','stringLiteralDataOffset','stringLiteralDataSize','stringOffset','stringSize','eventsOffset','eventsSize','propertiesOffset','propertiesSize','methodsOffset','methodsSize','parameterDefaultValuesOffset','parameterDefaultValuesSize','fieldDefaultValuesOffset','fieldDefaultValuesSize','fieldAndParameterDefaultValueDataOffset','fieldAndParameterDefaultValueDataSize','fieldMarshaledSizesOffset','fieldMarshaledSizesSize','parametersOffset','parametersSize','fieldsOffset','fieldsSize','genericParametersOffset','genericParametersSize','genericParameterConstraintsOffset','genericParameterConstraintsSize','genericContainersOffset','genericContainersSize','nestedTypesOffset','nestedTypesSize','interfacesOffset','interfacesSize','vtableMethodsOffset','vtableMethodsSize','interfaceOffsetsOffset','interfaceOffsetsSize','typeDefinitionsOffset','typeDefinitionsSize','imagesOffset','imagesSize','assembliesOffset','assembliesSize','fieldRefsOffset','fieldRefsSize','referencedAssembliesOffset','referencedAssembliesSize','attributeDataOffset','attributeDataSize','attributeDataRangeOffset','attributeDataRangeSize','unresolvedVirtualCallParameterTypesOffset','unresolvedVirtualCallParameterTypesSize','unresolvedVirtualCallParameterRangesOffset','unresolvedVirtualCallParameterRangesSize','windowsRuntimeTypeNamesOffset','windowsRuntimeTypeNamesSize']
h=dict(zip(names,H))
print('version',h['version'],'types',h['typeDefinitionsSize']//88,'methods',h['methodsSize']//32,'fields',h['fieldsSize']//12)
S=h['stringOffset']; SS=h['stringSize']
def s(idx):
    e=d.index(b'\0', S+idx)
    return d[S+idx:e].decode('utf-8','replace')
T=h['typeDefinitionsOffset']
def type_at(i):
    v=struct.unpack_from('<16I8H2I', d, T+i*88)
    return dict(name=s(v[0]), ns=s(v[1]), byval=v[2], decl=v[3], parent=v[4], elem=v[5], gc=v[6], flags=v[7],
                fieldStart=v[8], methodStart=v[9], eventStart=v[10], propStart=v[11], nestedStart=v[12], ifaceStart=v[13], vtableStart=v[14], ifaceOffStart=v[15],
                method_count=v[16], prop_count=v[17], field_count=v[18], event_count=v[19], nested_count=v[20], vtable_count=v[21], iface_count=v[22], ifaceoff_count=v[23], bitfield=v[24], token=v[25])
M=h['methodsOffset']
def method_at(i):
    v=struct.unpack_from('<6I4H', d, M+i*32)
    return dict(name=s(v[0]), decl=v[1], ret=v[2], paramStart=v[3], gc=v[4], token=v[5], flags=v[6], iflags=v[7], slot=v[8], pcount=v[9])
types=[type_at(i) for i in range(h['typeDefinitionsSize']//88)]
pat=re.compile(r'aim|assist|hitbox|hit_box|headshot|head_shot|recoil|spread|bullet|ballistic|damage|firearm|shoot|weapon', re.I)
hits=[(i,t) for i,t in enumerate(types) if pat.search(t['name']) or pat.search(t['ns'])]
print('type hits',len(hits))
for i,t in hits:
    print(f"T{i} {t['ns']}.{t['name']} methods={t['method_count']} fields={t['field_count']} decl={t['decl']}")
