# Data files (not committed)

The decrypted `global-metadata.dec.dat` (55 MB) and the encrypted
`assembly-csharp-patch.enc.bin` are kept only in the local analysis workspace:

```
analysis/data/global-metadata.dec.dat
analysis/data/assembly-csharp-patch.enc.bin
```

They are game assets and are intentionally excluded from this public repo.
Regenerate the decrypted metadata from the official XAPK with
`analysis/scripts/decrypt_metadata.py` (XOR key `0xE8`).
