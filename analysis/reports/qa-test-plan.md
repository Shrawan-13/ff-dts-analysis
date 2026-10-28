# QA Validation Plan — Free Fire MAX 2.133.1 Headshot Cheat Vectors

**Document status:** Final draft for QA / security approval  
**Related report:** `reports/report.md`  
**Scope:** authorized private test environment only  
**Classification:** Internal anti-cheat validation — do not distribute

---

## 1. Purpose

The static analysis in `report.md` proves that the clean 2.133.1 client
contains the surfaces a headshot cheat would need. It does **not** prove that
the live server accepts them. This plan defines the controlled tests that turn
static evidence into dynamic proof (or into a documented mitigation).

The plan is designed to answer four questions:

1. Does the reported “first body, then head” pattern reproduce when the
   client-side aim/aim-assist surface is exercised?
2. Does the server trust the client’s hit body part / collider type?
3. Does head scaling or UGC hitbox manipulation change live hit registration?
4. Does the anti-cheat/telemetry detect any of the above?

---

## 2. Authorization and safety

**Required before any test:**

- Written approval from the game owner/security owner.
- Private test server and test build matching the production build under test.
- Dedicated test accounts; no real players, no production matchmaking.
- Security engineering owns and controls any instrumented test client.
- Data handling plan for captures/logs; no distribution of test tools.
- A stop condition owner who can halt the test immediately.

**Non-goals:**

- Do not test on live production.
- Do not distribute a cheat, mod, patch, or bypass.
- Do not use real player accounts or real player data.
- Do not publish exploit details outside the approved group.

**Stop conditions:**

- Any sign of impact on production or real players.
- Detection/anti-cheat alert that cannot be contained.
- Client/server instability, crash loops, or data corruption.
- Any request to test outside the approved environment.

---

## 3. Roles

| Role | Responsibility |
|---|---|
| QA lead | Owns the test plan, schedule, evidence, and final report |
| Security engineer | Builds and controls the instrumented test client; owns surface instrumentation |
| Server engineer | Provides private server, telemetry, logs, and server-side hit validation data |
| Data analyst | Parses captures/logs, computes metrics, produces charts/tables |
| Observer | Independent witness; confirms test conditions and evidence integrity |
| Approver | Security/management owner; approves start/stop and final conclusions |

---

## 4. Environment and test data

### 4.1 Environment

- Private test server running the same build/config as production for the
  features under test.
- Two test devices/accounts: attacker and target.
- Packet capture on the client and/or server.
- Server telemetry: shot events, hit events, damage events, body part,
  collider type, aim delta, validation results.
- Client logs and screen recording.
- A controlled test map/area with fixed distance and no third parties.

### 4.2 Test data

- One automatic weapon with a known, stable recoil/spread profile.
- Fixed distance(s): close (5 m), mid (15 m), long (30 m).
- Target stationary first; then strafing; then crouching.
- 30 trials per test case (or a statistically justified alternative).
- Baseline control: unmodified client, same weapon/map/distance.

### 4.3 Metrics

| Metric | Definition |
|---|---|
| First-shot body rate | % of trials where shot 1 is body/limb |
| Subsequent headshot rate | % of shots 2..N that are head |
| Server-accepted headshot rate | % of head hits the server accepts as head damage |
| Client vs server body part | Agreement between client-reported and server-recomputed hit part |
| Aim delta | Angular change between consecutive shots / frames |
| Time to kill | Shots/time to down the target |
| Detection events | Anti-cheat/telemetry alerts per trial |
| Exception rate | Crashes, rejects, desyncs per trial |

---

## 5. Test cases

Each case uses the same structure: objective, preconditions, instrumentation,
procedure, expected vulnerable result, expected mitigated result, evidence, and
pass/fail. The security engineer implements the instrumented client; QA runs
the procedure and records evidence.

---

### QA-01 — Baseline control

**Objective:** Establish normal hit registration and server behavior with an
unmodified client.

**Preconditions:** clean client, private server, test accounts, fixed weapon and
distance.

**Procedure:** Fire controlled bursts at the target’s body and head; record
client-reported and server-recomputed hit parts.

**Expected (control):** Body shots register as body/limb; head shots register
as head; server and client agree; no detection events.

**Evidence:** packet capture, server logs, CSV of shot/hit/damage, video.

**Pass/fail:** Pass if baseline is stable and metrics are recorded. This is the
comparison baseline for all other tests.

---

### QA-02 — Aim-assist lock to head (Vector A)

**Objective:** Determine whether exercising the aim-assist lock surface to the
target’s head produces the reported “first body, then head” pattern and whether
the server accepts it.

**Preconditions:** QA-01 complete; instrumented client approved; aim-assist
target surface available in the test build.

**Instrumentation / observation points:**

- Target selection / heuristic target.
- Locked aim-assist collider.
- Aim rotation and aux-aim rotation.
- Shot direction and hit body part.
- Server acceptance/rejection.

**Procedure:** In the instrumented client, exercise the aim-assist lock surface
so that shot 1 is taken at the target’s body/center and shots 2..N use the
target’s head collider as the lock target. Keep fire held for a fixed burst.
Repeat 30 trials at each distance. The security engineer owns the
implementation; QA records only the observable behavior.

**Expected vulnerable result:** Shot 1 body; shots 2..N head; server accepts
head damage; no immediate rejection. Aim delta may be gradual or within the
server’s tolerance.

**Expected mitigated result:** Server rejects head hits, recomputes body, or
flags the aim delta; no “first body, then head” pattern.

**Evidence:** packet capture, server validation logs, aim-delta CSV, video,
detection events.

**Pass/fail:** Vulnerable if the pattern reproduces in ≥80% of trials and the
server accepts head damage. Mitigated if the server rejects or the pattern does
not reproduce.

---

### QA-03 — Aim-rotation override (Vector A)

**Objective:** Determine whether a direct aim-rotation write to the head is
accepted, independent of the aim-assist lock.

**Preconditions:** QA-01 complete; instrumented client approved.

**Instrumentation / observation points:**

- Aim rotation / current aim rotation.
- Shot direction.
- Server validation of angle delta.
- Hit body part.

**Procedure:** In the instrumented client, exercise the aim-rotation surface so
the shot direction points at the target’s head at the moment of fire. Compare
with QA-01. Repeat 30 trials.

**Expected vulnerable result:** Head hits accepted; server does not reject the
angle change.

**Expected mitigated result:** Server rejects the shot or flags the delta; hit
is recomputed as body/miss.

**Evidence:** aim-delta CSV, packet capture, server logs, video.

**Pass/fail:** Vulnerable if head hits are accepted in ≥80% of trials without
detection. Mitigated otherwise.

---

### QA-04 — Body collider reported as Head (Vector B)

**Objective:** Determine whether the server trusts a client-reported body part
when a body collider is reported as `Head`.

**Preconditions:** QA-01 complete; instrumented client approved; a controlled
body hit.

**Instrumentation / observation points:**

- Client-reported collider type / body part.
- Server-recomputed body part.
- Damage applied.
- Detection events.

**Procedure:** In the instrumented client, simulate a body hit whose reported
body part is `Head` (the security engineer owns the synthetic event). Fire at
the body; record the client report and the server result. Repeat 30 trials.

**Expected vulnerable result:** Server accepts the hit as head damage; damage
matches head multiplier.

**Expected mitigated result:** Server recomputes body/limb and rejects the
head claim; detection event.

**Evidence:** client report vs server recompute CSV, damage values, packet
capture, server logs.

**Pass/fail:** Vulnerable if the server accepts ≥80% of body-as-head reports.
Mitigated if it recomputes/rejects.

---

### QA-05 — Forged damage info with Head (Vector B)

**Objective:** Determine whether a forged damage-info body part is accepted by
the damage path.

**Preconditions:** QA-01 complete; instrumented client approved.

**Instrumentation / observation points:**

- Damage info body-part field.
- `TakeDamage` path.
- Server damage validation.
- Damage applied.

**Procedure:** In the instrumented client, simulate a damage event with the
body part set to `Head` on a controlled body hit. Record server response.
Repeat 30 trials.

**Expected vulnerable result:** Head damage applied; no rejection.

**Expected mitigated result:** Server rejects or recomputes; detection event.

**Evidence:** damage event logs, server validation, packet capture.

**Pass/fail:** Vulnerable if head damage is applied in ≥80% of trials.
Mitigated otherwise.

---

### QA-06 — Big-head / head-bone scaling (Vector C)

**Objective:** Determine whether enlarging the enemy head collider/bone changes
live hit registration.

**Preconditions:** QA-01 complete; instrumented client approved; big-head
surface available in the test build.

**Instrumentation / observation points:**

- Head collider scale.
- Head bone scale.
- Hit registration point.
- Server-recomputed hit part.
- Damage.

**Procedure:** In the instrumented client, exercise the head-scale surface on
the target (start with a modest scale, then a larger scale). Fire at the
neck/upper chest. Compare with QA-01. Repeat 30 trials.

**Expected vulnerable result:** Body/neck shots register as head; server
accepts.

**Expected mitigated result:** Server uses its own hitbox and registers
body/limb; no change.

**Evidence:** scale values, hit-point CSV, server recompute, video.

**Pass/fail:** Vulnerable if the scaled collider changes hit registration and
the server accepts in ≥80% of trials. Mitigated otherwise.

---

### QA-07 — UGC custom hitbox / aim-assist entity (Vector D)

**Objective:** Determine whether a private UGC map can define a head hitbox or
aim-assist entity that changes hit registration.

**Preconditions:** QA-01 complete; private UGC test map; server UGC validation
enabled; instrumented client approved.

**Instrumentation / observation points:**

- UGC body-part definition.
- Custom hitbox collider.
- UGC aim-assist entity distance/offset.
- Local integrity validator result.
- Server UGC validation result.

**Procedure:** Load a private UGC test map with a controlled body-part/hitbox
definition and, separately, a UGC aim-assist entity near the head. Fire at the
target and record hit registration and validation results. Repeat 30 trials.

**Expected vulnerable result:** UGC hitbox/aim-assist changes hit registration;
local/server validation accepts or is bypassed.

**Expected mitigated result:** Local SHA1/integrity check or server validation
rejects the map; no change.

**Evidence:** UGC validation logs, hit registration CSV, video, server logs.

**Pass/fail:** Vulnerable if the UGC change is accepted and changes hit
registration in ≥80% of trials. Mitigated otherwise.

---

### QA-08 — Unsigned iFix patch (Vector E)

**Objective:** Determine whether the iFix loader accepts an unsigned test patch
and whether the anti-cheat detects it.

**Preconditions:** QA-01 complete; test build with loader logging; approved test
patch signed/unsigned as required by the test; no production.

**Instrumentation / observation points:**

- Patch load call and result.
- Patch authenticity/signature check.
- Detection events.
- Runtime behavior change.

**Procedure:** In the controlled test build, attempt to load a test patch
through the documented loader path. Record whether it loads, whether a
signature check occurs, and whether detection fires. Do not use a patch that
changes production behavior.

**Expected vulnerable result:** Unsigned patch loads; no signature check; no
detection.

**Expected mitigated result:** Loader rejects the patch; signature check;
detection event.

**Evidence:** loader logs, signature-check logs, detection events, video.

**Pass/fail:** Vulnerable if an unsigned patch loads without detection.
Mitigated if rejected/flagged.

---

### QA-09 — Config/debug tampering (Vector F)

**Objective:** Determine whether debug/config aim-assist values are active and
client-authoritative in a release-like build.

**Preconditions:** QA-01 complete; release-like test build; config/debug surface
available.

**Instrumentation / observation points:**

- `DebugWeaponAimAssist*` values.
- `extra_hitbox_*` values.
- Aim-assist behavior.
- Server acceptance/detection.

**Procedure:** In the controlled test build, vary the debug/config values within
approved bounds and measure aim-assist behavior and hit registration. Compare
with QA-01.

**Expected vulnerable result:** Values change aim assist/hit registration; no
server override/detection.

**Expected mitigated result:** Values are ignored, gated, or server-overridden;
detection event.

**Evidence:** config values, aim-assist metrics, server logs, video.

**Pass/fail:** Vulnerable if the values change behavior in a release-like build.
Mitigated otherwise.

---

### QA-10 — Detection and telemetry validation

**Objective:** Confirm that the server/anti-cheat records the signals needed to
detect the above vectors.

**Preconditions:** QA-02..QA-09 executed at least once; telemetry enabled.

**Instrumentation / observation points:**

- Body part, collider type, shot direction, aim delta.
- Client-reported vs server-recomputed hit part.
- Head-scale values.
- Patch-load events.
- Config changes.

**Procedure:** Re-run a subset of QA-02..QA-09 and verify that each signal
appears in telemetry and that the detection rules fire where expected.

**Expected result:** All required signals are present; detection rules can
distinguish normal vs abnormal.

**Evidence:** telemetry export, detection events, dashboard screenshots.

**Pass/fail:** Pass if the signals are present and actionable; fail if blind
spots remain.

---

## 6. Evidence collection

For each test, capture:

- Test ID, date/time, build hash, server build, device models, accounts.
- Packet capture (client/server) with timestamps.
- Server telemetry export (CSV/JSON).
- Client logs.
- Screen recording (full session).
- Screenshots of key frames.
- Completed result table.

Naming convention:

```
QA-<id>_<date>_<build>_<attacker>_<target>_<distance>_<trial>.<ext>
```

Store in the approved secure location; do not commit captures or tools to a
public repo.

---

## 7. Acceptance criteria / proof standard

The 80% thresholds below are proposed defaults; QA/security can adjust them
with a statistical review before the test. The important point is that the
criteria are defined before execution and applied consistently.

| Test | Vulnerable if | Mitigated if |
|---|---|---|
| QA-02 | First body + subsequent head in ≥80% of trials; server accepts head | Server rejects or pattern absent |
| QA-03 | Head hits accepted in ≥80% of trials | Server rejects/flags |
| QA-04 | Body-as-head accepted in ≥80% of trials | Server recomputes/rejects |
| QA-05 | Forged Head damage applied in ≥80% of trials | Server rejects/recomputes |
| QA-06 | Scaled head changes hit registration and is accepted | Server uses fixed hitbox |
| QA-07 | UGC change accepted and changes hit registration | Integrity/server validation rejects |
| QA-08 | Unsigned patch loads without detection | Loader rejects/flags |
| QA-09 | Debug/config values change behavior in release-like build | Values ignored/gated |
| QA-10 | Required signals present and actionable | Blind spots remain |

**Overall proof:** the reported cheat is “live-practical” only if QA-02 or
QA-04 passes **and** QA-10 shows the behavior is observable. If only QA-02
passes, the vector is aim-based; if only QA-04 passes, it is body-part trust.
If both fail, the server-side validation is sufficient for those vectors, and
the remaining vectors (C/D/E/F) must be assessed separately.

---

## 8. Reporting template

```
Test ID:
Vector:
Build / server:
Date / time:
Devices / accounts:
Distance / stance:
Trials:
Result: PASS (vulnerable) / FAIL (mitigated) / INCONCLUSIVE
Metrics:
  first-shot body rate:
  subsequent headshot rate:
  server-accepted headshot rate:
  client vs server body part agreement:
  aim delta:
  detection events:
Evidence paths:
Observations:
Recommendation:
```

---

## 9. Appendix — telemetry fields to capture

```
timestamp
match_id
attacker_id
target_id
weapon_id
shot_index
shot_origin
shot_direction
aim_rotation
aim_delta_deg
client_reported_body_part
server_recomputed_body_part
client_reported_collider_type
server_recomputed_collider_type
hit_position
damage
damage_multiplier
head_collider_scale
patch_load_event
patch_signature_result
config_values
detection_rule_id
detection_result
```

---

## 10. Notes for QA

- The instrumented client is a test harness, not a production cheat. Security
  engineering must control it and remove it after the test.
- Do not use the live game or real accounts.
- If a test cannot be run safely, mark it **INCONCLUSIVE** and document why.
- A failed test is a useful result: it proves the server-side mitigation works
  for that vector.
