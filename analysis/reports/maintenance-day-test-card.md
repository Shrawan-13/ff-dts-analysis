# Maintenance-Day Live Test Card — Headshot Cheat Vectors

**Use:** authorized maintenance window only  
**Client:** company-approved debug/test client on a company testing device  
**Rule:** use only the approved client’s existing features; no third-party mods,
no production players, no real player data.

**Goal:** give QA a simple pass/fail test and capture server-side proof that
higher staff can trust.

---

## 1. Pre-flight checklist

Complete before any test:

- [ ] Written approval from the security owner — name/date: ____________
- [ ] Environment confirmed: maintenance mode / private test server
- [ ] No players other than QA/dev/test accounts
- [ ] Build/package version: ____________
- [ ] Test accounts: attacker ____________ / target ____________
- [ ] Company-approved debug client installed and verified
- [ ] Feature list confirmed (see section 2)
- [ ] Server verbose logging enabled; log location: ____________
- [ ] Screen recording ready
- [ ] Packet capture ready (if server team wants it)
- [ ] Rollback/restore plan confirmed
- [ ] Stop-condition owner: ____________
- [ ] Secure evidence storage: ____________

If any item is missing, do not start the test.

---

## 2. Feature check

Mark what the approved client can actually do. If a feature is missing, mark the
corresponding test **N/A** — do not improvise.

- [ ] Aim-assist / target-lock control
- [ ] Hit-part control
- [ ] Head scale / big-head control
- [ ] UGC custom map / custom hitbox
- [ ] Debug overlay / telemetry
- [ ] Bot/target spawning

---

## 3. Tests

### M-01 — Baseline

**Setup:** all special features off; normal client behavior.

**Do:** fire controlled bursts at the target’s body and head.

**Look for:**
- Body shots register as body/limb.
- Head shots register as head.
- Server and client agree.
- No detection alerts.

**Result:** ☐ PASS (baseline stable) ☐ FAIL (explain) ☐ N/A

---

### M-02 — Aim-assist head lock (Vector A)

**Setup:** enable the approved aim-assist / target-lock feature to the head, if
available. If the client has no such control, mark **N/A**.

**Do:** first shot at the body, then hold fire for 5–10 shots.

**Look for:**
- Shot 1: body/center.
- Shots 2+: head.
- Server accepts head damage.
- No immediate rejection or detection alert.

**Result:** ☐ PASS (first body, then head; server accepts)  
☐ FAIL (no pattern or server rejects) ☐ N/A

**Evidence:** video, server log, packet capture.

---

### M-03 — Hit-part head (Vector B)

**Setup:** enable the approved hit-part control, if available. If not, **N/A**.

**Do:** fire at the target’s body; repeat 10 times.

**Look for:**
- Server accepts the body hit as head damage; or
- Server recomputes body/limb and rejects the head claim.

**Result:** ☐ PASS (server accepts body-as-head)  
☐ FAIL (server recomputes/rejects) ☐ N/A

**Evidence:** client report vs server recompute, damage values, video.

---

### M-04 — Big head / head scale (Vector C)

**Setup:** enable the approved big-head / head-scale feature, if available. If
not, **N/A**.

**Do:** fire at the target’s neck/upper chest; repeat 10 times.

**Look for:**
- Body/neck shots register as head; or
- Server uses its own hitbox and registers body/limb.

**Result:** ☐ PASS (scale changes hit registration; server accepts)  
☐ FAIL (no change / server rejects) ☐ N/A

**Evidence:** scale value, hit-point log, video.

---

### M-05 — UGC custom hitbox (Vector D)

**Setup:** load a private UGC test map with a controlled body-part/hitbox
definition, if available. If not, **N/A**.

**Do:** fire at the target; repeat 10 times.

**Look for:**
- UGC hitbox changes hit registration; or
- Local SHA1/integrity check or server validation rejects the map.

**Result:** ☐ PASS (UGC change accepted)  
☐ FAIL (validation rejects) ☐ N/A

**Evidence:** UGC validation logs, hit registration, video.

---

### M-06 — Mitigation A/B

**Setup:** patched/mitigated build, if available.

**Do:** repeat M-02 and M-03.

**Look for:**
- The behavior is blocked/rejected on the mitigated build.

**Result:** ☐ PASS (mitigation blocks behavior)  
☐ FAIL (behavior still works) ☐ N/A

**Evidence:** side-by-side video, server logs.

---

### M-07 — Telemetry / server log check

**Do:** after each test, ask the server team to export the verbose log for that
session.

**Look for:**
- Attacker/target IDs.
- Shot index.
- Client-reported body part.
- Server-recomputed body part.
- Hit accepted/rejected.
- Damage.
- Aim delta.
- Detection events.

**Result:** ☐ PASS (signals present) ☐ FAIL (blind spot) ☐ N/A

---

## 4. Evidence to capture

For every test:

- Test ID and result.
- Date/time, build hash, server build.
- Attacker/target accounts.
- Video of the full session.
- Server log export.
- Packet capture (if requested).
- Screenshots of key frames.
- Completed test card.

Naming:

```
M-<id>_<date>_<build>_<attacker>_<target>.<ext>
```

---

## 5. Stop conditions

Stop immediately if:

- any real player is affected;
- the environment is not actually isolated;
- the client/server crashes repeatedly;
- a detection alert cannot be contained;
- anyone asks to test outside the approved environment;
- evidence cannot be captured securely.

---

## 6. Reporting

For each test:

```
Test ID:
Result: PASS / FAIL / N/A
Observed behavior:
Server accepted? yes / no / unknown
Evidence paths:
Notes:
```

**Overall proof:** Vector A or B is live-practical only if M-02 or M-03 passes
**and** M-07 shows the server accepted the hit. If the server
rejects/recomputes, that vector is mitigated for this build. Vectors C/D are
separate; test them only if the approved client supports them.

---

## 7. Notes for QA

- You do not need to understand the metadata or the reverse-engineering report.
- Use only the approved client features; do not install anything else.
- A failed test is a useful result: it proves the mitigation works.
- If you are unsure, mark **N/A** and ask the security owner; do not improvise.
