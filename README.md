# Free Fire MAX client analysis (hackathon)

Static analysis of the provided `com.dts.freefiremax` 2.133.1 XAPK to identify
which **client-side** mechanics could produce the observed cheat pattern:

> first bullet hits body, subsequent bullets while holding fire hit head

The input XAPK is attached to the `input` release (not committed to git).
The workflow extracts `libil2cpp.so` + `global-metadata.dat`, decrypts the
metadata (single-byte XOR `0xE8`), runs Il2CppDumper, and publishes a compact
report plus raw dump artifacts.

## Run

Actions -> **IL2CPP analysis** -> Run workflow.

## Notes

- `global-metadata.dat` is XOR-0xE8 obfuscated; `scripts/decrypt_metadata.py`
  normalizes it to the standard `0xFAB11BAF` header.
- The full `dump.cs` / `script.json` are workflow artifacts, not committed.
- This repo is for defensive/anti-cheat research only.
