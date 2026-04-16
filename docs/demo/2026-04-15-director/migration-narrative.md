# Migration Architecture Narrative

**Generated:** 2026-04-15
**Project:** director-demo-2026-04-15
**Pipeline stage:** analyzed
**Decision summary:** 82 total decisions (25 pending, 57 resolved, 15 architecture advisories)

---

## Executive Summary

This is a mid-sized CUCM cluster migration: 277 users, 1,100 device records (681 hardware phones + 314 Webex App + 91 incompatible + 10 infrastructure), and 6 locations spread across what appears to be a US-centric demo footprint (dCloud lab + named branches: New York, Chicago, San Jose). The bulk of migration risk is **not** in user provisioning — 89% of phones (611 convertibles + 70 native MPP) move via in-place activation-code conversion, no hardware refresh required. Risk concentrates in three areas: **(1) PSTN architecture** (17 SRST-equipped SIP trunks force a Local Gateway design rather than Cloud Connected PSTN), **(2) dial-plan flattening** (11 route patterns carry CPN transformation chains that Webex models flat per user/location), and **(3) E911 reconfiguration** (304 ECBN configs and 5 CER ELIN translation patterns require a separate workstream — operator has accepted the demo gap).

What the admin should pay most attention to: the three HIGH-severity architecture advisories collectively describe the routing topology that must be designed before any phone is migrated. They are not deferrable — every decision downstream (trunk type, dial plan scope, route group bindings) cascades from these. Beyond those, **55 Remote Destination Profiles for 0 users** is a data-quality red flag worth investigating before plan time, and the **3 dCloud CER workspace-type-uncertain decisions** are the only items in the queue requiring explicit operator input.

The 91 incompatible devices (already resolved as DEVICE_INCOMPATIBLE → bulk replacement advisory D0943) and 51 FORWARDING_LOSSY decisions (CUCM-only callForwardBusyInt / NoCoverage / NotRegistered variants) represent expected fidelity loss — accept-loss is the correct posture and the static recommendations are sound.

## Cross-Decision Analysis

### LGW + CPN transformations + E911 form a single trunk-design workstream

Decisions **D0948** (PSTN: Local Gateway), **D0947** (CPN transformations on 11 route patterns), and **D0951** (E911 separate workstream) are presented as three independent advisories but are one design problem. The 17 carrier SIP trunks have SRST configured (D0948 → LGW), 11 of those route patterns carry calling/called party transformation masks (D0947), and 5 of the 17 translation patterns are E911 ELIN (D0951). All three terminate on the same on-prem SBC topology. Conclusion: the operator must produce one Local Gateway design that simultaneously (a) carries the LGW trunks, (b) preserves the carrier-required ANI/DNIS manipulation, and (c) handles ELIN insertion for emergency callbacks. Treating these as parallel tracks risks an SBC config that solves one problem and breaks another.

### Remote Destination Profile / SNR data discontinuity

Advisory **D0953** reports "55 remote destinations for 0 users." The inventory confirms 55 `remote_destination` and 56 `info_device_profile` (Extension Mobility) objects — but the SNR pattern attributes them to zero users. This is either (a) the SNR-to-user link is broken in normalization (RDPs orphaned during EM profile mapping), or (b) the demo dataset has dangling SNR profiles from old EM users. Either way, no SNR migration ops will be emitted at plan time. If the source CUCM actually has live SNR users, this is a silent drop. Cross-reference with **D0955** (56 EM profiles → hot desking) before accepting D0953 — the same 55–56 device profile count appearing in both advisories suggests they describe the same underlying object set.

### Workspace type uncertainty cascades into license-tier decisions

The 3 `WORKSPACE_TYPE_UNCERTAIN` decisions (D0365, D0370, D0373 — dCloud_CER_P1/P2/P3) and the 4 `WORKSPACE_SETTINGS_PROFESSIONAL_REQUIRED` decisions (D0367, D0369, D0372, D0375 — same dCloud CER ports plus Hotel Room 1100) overlap on the same physical devices. The CER ports are CTI route points functioning as ELIN callback endpoints — they are infrastructure, not workspace phones. Classifying them as "meetingRoom" or "desk" is forcing an inappropriate abstraction. See dissent on D0365/D0370/D0373 below.

### 405 unknown phones vs. 91 incompatible totals

Advisory **D0943** reports "405 unknown phones need bulk replacement" but the launch context says 91 incompatible. The 405 figure likely includes the 314 Webex App soft clients (already-Webex, no replacement needed) plus other non-hardware records misclassified as "unknown" model. Verify the 91 hardware-incompatible count is the true replacement scope before sizing a hardware refresh quote.

## Dissent Flags

### Dissent: D0948 (PSTN: Local Gateway) — supports static, escalates cascades

**Static recommendation:** accept — "Carrier SIP trunks with SRST (17). Recommendation: Local Gateway — survivability requirement means a local SBC is needed."
**Advisor alternative:** accept the LGW recommendation but treat it as a compound decision, not a single accept. The 17 trunks are not classified by **REGISTERING vs CERTIFICATE_BASED** — and Webex trunk type is IMMUTABLE after creation. A wrong choice forces delete/recreate during cutover, which tears down route-group bindings and causes a 15–30 minute calling outage.
**Confidence:** HIGH
**KB source:** kb-trunk-pstn.md §Dissent Triggers, entry **DT-TRUNK-004**
**Admin action:** Before plan phase, confirm the exact SBC vendor/model terminating each of the 17 trunks. Cisco IOS-XE CUBE → REGISTERING; AudioCodes/Ribbon/Oracle/Sonus → CERTIFICATE_BASED. Do not let the migration plan proceed with any trunk in `needs_type_decision`.

### Dissent: D0947 (CPN transformations) — accept but flag CCPP impossibility

**Static recommendation:** accept — "11 route patterns and 0 trunks have calling/called party number transformations configured. CUCM applies these transformations in a chain — Webex uses flat caller ID per user/location."
**Advisor alternative:** accept, but use this finding to lock the PSTN connection type to LGW even if D0948 were borderline. Cloud Connected PSTN cannot reproduce arbitrary CPN transformation chains — the carrier-specific manipulation has to happen on a customer-controlled SBC. This is a second independent vote for LGW beyond the SRST signal.
**Confidence:** LOW (the LGW recommendation already wins on SRST grounds; this is corroboration, not override)
**KB source:** kb-trunk-pstn.md §Dissent Triggers, entry **DT-TRUNK-002**
**Admin action:** Document which carrier-required ANI/DNIS transformations must move to the SBC config. CUCM transformation masks at the route pattern level become dial-peer translation rules on IOS-XE CUBE or message manipulation rules on a third-party SBC.

### Dissent: D0365 / D0370 / D0373 (dCloud_CER_P1/P2/P3 workspace type) — recommend `other`, not `meetingRoom`

**Static recommendation:** none (3 needs-input decisions; static rule returned `None` because the device pool is empty and the model is not in `_DESK_PHONE_MODELS` or `_CONFERENCE_MODELS`).
**Advisor alternative:** Use workspace type `other`. The device names dCloud_CER_P1/P2/P3 and display name "dCloud CER Port N" indicate these are Cisco Emergency Responder ELIN callback endpoints — CTI route points that receive PSAP callbacks, not workstations. They have no human user, no conference room, no desk. `other` is the only honest classification (Webex semantics: "lobby phone, break room, etc." — i.e., shared infrastructure phones). Picking `meetingRoom` falsely tags them as collaboration endpoints; `desk` implies hot-desking semantics they cannot provide.
**Confidence:** MEDIUM (correct on the categorization but the operator should also evaluate whether these CER ports should migrate at all — Webex E911 is handled by the cloud-native ECBN model, not by ELIN translation patterns)
**KB source:** kb-user-settings.md §Dissent Triggers, entry **DT-USER-005**
**Admin action:** Confirm whether the Webex E911 design replaces the CER ELIN flow entirely. If yes, these 3 devices likely should be skipped, not migrated as workspaces. If retained as a parallel ELIN-callback path during coexistence, classify as `other`.

### Dissent: D0953 (55 SNR remote destinations) — investigate the "0 users" anomaly

**Static recommendation:** accept — "55 remote destinations for 0 users — Webex SNR is simpler, manual setup required."
**Advisor alternative:** Do not accept until the user-link discontinuity is resolved. If the 55 RDPs map to real CUCM users in the source data, those users will silently lose Single Number Reach at cutover with no announcement. Per DT-USER-006, SNR / simultaneousRing / sequentialRing cannot be migrated via admin-token API at all — they require user-level OAuth at `/people/me/settings/`. The "0 users" count suggests the link is already broken in the canonical model, but accepting the advisory before verifying causes a silent functional regression.
**Confidence:** HIGH
**KB source:** kb-user-settings.md §Dissent Triggers, entry **DT-USER-006**
**Admin action:** Run `wxcli cucm inventory` joined against `remote_destination.user_id` to confirm whether RDPs have associated users. If yes, generate a per-user SNR self-service guide and include it in the user notice. If genuinely orphaned, accept the advisory and document the cleanup.

### Dissent: D0367 / D0369 / D0372 / D0375 (Workspace Professional required) — supports static for the dCloud CER ports, escalates Hotel Room 1100

**Static recommendation:** accept_loss — "voicemail/callForwarding settings will be lost with basic Workspace license."
**Advisor alternative:** Accept loss for the 3 dCloud CER ports (D0367, D0372, D0375) — voicemail on a CTI route point is not a user-facing feature and dropping it is correct. **Reject accept_loss for D0369 (Hotel Room 1100)** — a hotel room phone with call forwarding configured is using forwarding for housekeeping/wake-up routing or business continuity, which is exactly the case DT-USER-002 describes. Recommend upgrading this single workspace to Professional rather than silently losing the forwarding behavior.
**Confidence:** MEDIUM
**KB source:** kb-user-settings.md §Dissent Triggers, entry **DT-USER-002**
**Admin action:** Verify Hotel Room 1100's call forwarding target before accepting loss. If forwarding to a front desk / housekeeping queue, upgrade to Professional. If forwarding only to voicemail (which Basic supports via `/workspaces/{id}/features/`), accept_loss is fine.

## Domain Summaries

### Trunk / PSTN

17 SIP trunks, all SRST-equipped, terminating on what appears to be a multi-IP SBC topology (4 trunks → 198.18.135.54, 2 trunks → 198.18.133.150 — both flagged for consolidation by D0944 and D0945). The static rule recommends Local Gateway (D0948) and the consolidation advisories suggest collapsing the duplicate destinations. Three open questions: (1) trunk type per DT-TRUNK-004; (2) whether the 4 trunks to .135.54 actually serve different routing purposes per DT-TRUNK-001; (3) hybrid dial plan style (D0949: 25% E.164) means the trunk design must handle both globalized and on-net localized addressing.

### Dial plan / CSS

44 route patterns, 17 translation patterns, 14 partitions, 9 CSSes — modest in size. The CPN transformation chains on 11 route patterns (D0947) are the headline finding. Two translation patterns duplicate native Webex normalization (D0942) and can be eliminated. Three partitions trigger selective-call-handling rebuild (D0956: "Directory URI", "E911", "Emergency_PT" — D0939, D0940, D0941). The E911 partition (D0939) has 1 DN reachable from only 1 of 9 CSSes — classic VIP/priority bypass pattern; this becomes a Webex Selective Accept rule, not a partition.

### Devices

611 convertibles auto-emit activation codes at plan time (no decision queue). 70 native MPPs migrate as-is. 91 incompatible models — bulk replacement advisory D0943 covers procurement. 56 Extension Mobility profiles map to Webex hot desking (D0955) but require user-level setup post-cutover. 6 BUTTON_UNMAPPABLE decisions cover Redial / Hunt Group Logout / similar CUCM-only buttons across DX80, DX70, and 8851 templates — accept_loss is correct (these buttons have no Webex equivalent).

### User settings

277 users, 51 with CUCM-only forwarding variants (callForwardBusyInt, NoCoverage, NotRegistered) — these are CUCM-internal-vs-external routing distinctions Webex collapses into single CFB / CFNA. Accept_loss is correct because the external-facing behavior (the only thing end users observe) is preserved. 14 users with call recording enabled (D0952) require per-user enable post-migration; if any of those 14 are workspaces, see DT-USER-004.

### Workspaces

7 workspace decisions total — 3 type-uncertain + 4 settings-loss. All 3 type-uncertain are dCloud CER ports (infrastructure). Of the 4 settings-loss, 3 are the same CER ports and 1 is Hotel Room 1100 (the only genuine business-context decision in the workspace queue).

### Voicemail / location

7 voicemail pilots can be eliminated (D0946) — Webex uses per-user voicemail; pilot consolidation is purely structural simplification. Verify per DT-FEAT-004 that no pilots represent language-localized greeting trees (the pilot names in this dataset don't appear to carry language markers, so the simplification is likely safe).

### E911

304 ECBN configs reference LOCATION_ECBN (operator has accepted this demo gap). Production migration would require per-number ECBN assignment under RAY BAUM's Act §506. The 5 ELIN translation patterns (D0951) belong to the CER decommission workstream, not the Webex provisioning pipeline.

## Risk Narrative

**1. PSTN cutover risk — HIGH.** The trunk-type immutability constraint (DT-TRUNK-004) means a wrong REGISTERING/CERTIFICATE_BASED choice forces delete-and-recreate during cutover. With 17 trunks, even a single misclassification can cause a multi-trunk outage. Mitigation: classify all 17 trunks before plan time, lab-test one of each type before bulk provisioning.

**2. CPN transformation regression — MEDIUM-HIGH.** 11 route patterns carry caller-ID transformations that the carrier may rely on for ANI screening, billing, or compliance. If these aren't reproduced on the LGW SBC, outbound calls may be rejected by the carrier or arrive at the called party with the wrong CLID. Mitigation: extract the transformation masks before cutover, map each one to an SBC dial-peer rule, test against the carrier in lab.

**3. SNR silent loss — MEDIUM.** 55 RDPs in the source data with 0 user attribution (D0953). If those are real users, they lose mobile twinning at cutover with no notice. Mitigation: verify the user link before accepting D0953; if real, prepare a self-service guide for affected users.

**4. E911 compliance during coexistence — MEDIUM.** The operator has accepted the LOCATION_ECBN demo gap, but production cutover requires per-number ECBN binding. Mitigation: defer to the separate E911 workstream as D0951 recommends, but block production cutover on its completion.

**5. Workspace type misclassification for CER ports — LOW.** 3 dCloud CER ports will be wrongly typed if the operator accepts the static recommendation suggestions. Mitigation: classify as `other`, or skip migration entirely if Webex ECBN replaces the CER ELIN flow.

## Questions for the Admin

**Q1: Trunk hardware vendor per trunk.** For each of the 17 SIP trunks, which physical SBC terminates it? (Cisco IOS-XE CUBE = REGISTERING; AudioCodes/Ribbon/Oracle/Sonus = CERTIFICATE_BASED.) This is required before the plan phase — see DT-TRUNK-004.

**Q2: Are the 4 trunks to 198.18.135.54 functionally distinct?** D0944 recommends consolidation but DT-TRUNK-001 cautions that same-destination trunks may serve different routing purposes (PSTN vs voicemail vs intercluster). What does each of the 4 do?

**Q3: Carrier CPN transformation requirements.** Which of the 11 transformation chains (D0947) are mandatory carrier requirements vs. legacy CUCM artifacts? The mandatory ones must move to the LGW SBC config; the artifacts can be dropped.

**Q4: 55 Remote Destination Profiles — orphaned or live?** D0953 reports 0 users attributed. Are these dangling profiles from decommissioned users (accept and clean up) or a normalization break (silent SNR loss for live users)?

**Q5: dCloud CER ports — migrate or retire?** If Webex ECBN replaces the CER ELIN flow, the 3 dCloud_CER_P1/P2/P3 devices likely should not migrate at all. If retained for coexistence, classify as `other`.

**Q6: Hotel Room 1100 forwarding target.** Where does the call forwarding go? If to a front desk / housekeeping queue, upgrade to Professional (DT-USER-002). If only to voicemail, accept_loss is fine.

**Q7: Bulk replacement scope confirmation.** D0943 reports 405 unknown phones; the launch context says 91 incompatible. Which is the true hardware refresh count? (Likely 91 hardware + 314 Webex App misclassified as "unknown" model = 405.)
