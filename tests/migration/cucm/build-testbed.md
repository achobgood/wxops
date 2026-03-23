# CUCM Lab Test Bed Build — Enterprise Migration Validation

**Role:** You are a senior CUCM administrator and developer with 10+ years of enterprise deployment experience. You've migrated clusters from 500 to 80,000 users across healthcare, financial services, manufacturing, and government. You know every AXL quirk, every edge case that breaks tooling, and every configuration pattern that enterprises use but vendors never test against.

**Goal:** Build a representative enterprise test dataset on CUCM 15.0 lab (10.201.123.107) that exercises every extraction path in the migration tool. This isn't a demo — it's a validation bed that must expose real-world parsing issues.

## Guiding Principles

1. **Test the ugly stuff.** Every enterprise has legacy cruft: users with no email, phones with no lines, shared lines spanning locations, SCCP devices that should've been upgraded years ago. If the extractor can't handle it, we find out here.

2. **Test relationships, not just objects.** The migration tool builds a cross-reference graph with 27 relationship types. Every relationship needs at least one instance in the test data. An orphaned object (phone with no pool, user with no device) is as important as a fully connected one.

3. **Test ordering and priority.** CSS partition ordering is the #1 data integrity risk in CUCM migrations. Build CSSes with enough partitions that a sorting bug would produce visibly wrong results.

4. **Test boundaries.** Multi-line phones (the max button count), long CSS chains, device pools that share a location (consolidation logic), shared lines across 3+ devices.

5. **Test every object type the extractors pull.** If there's a returnedTags constant in the code, there must be at least one real object exercising those fields.

## Pre-Build: Fix Admin Access

Before creating anything, the `admin` account needs the **Standard AXL API Access** role. Without it, `listEndUser` returns 403 and user extraction is completely blocked.

**Verification:** After fixing, `listEndUser` with `{'firstName': '%'}` should return results.

## Build Order

Objects have dependencies. Build in this order:

### Phase 1: Infrastructure (no dependencies)

1. **DateTime Groups** (2 new + CMLocal existing)
   - `DT-Eastern` → America/New_York
   - `DT-Pacific` → America/Los_Angeles
   - Validates: `timeZone` field extraction, multiple timezone handling

2. **CUCM Locations** (2 new + 3 existing)
   - `HQ` — primary site
   - `Branch-Austin` — branch office
   - Validates: `listLocation` / `getLocation`, location entity extraction

3. **Regions** (2 new + Default existing)
   - `HQ-Region`
   - `Branch-Region`
   - Validates: informational field extraction on device pools

4. **Device Pools** (4 new + Default existing)
   - `DP-HQ-Phones` → DT-Eastern, HQ location, HQ-Region
   - `DP-HQ-Softphones` → DT-Eastern, HQ location, HQ-Region (**same location as DP-HQ-Phones — tests consolidation**)
   - `DP-Branch-Phones` → DT-Pacific, Branch-Austin, Branch-Region
   - `DP-CommonArea` → DT-Eastern, HQ location, Default region
   - Validates: device pool → datetime group cross-ref, device pool → location cross-ref, multiple pools per location (consolidation), pool with no SRST

5. **Partitions** (5 new + 6 existing)
   - `Internal-PT` — internal extensions
   - `Local-PSTN-PT` — local/national PSTN
   - `LongDistance-PT` — long distance
   - `International-PT` — international dialing
   - `Block-Premium-PT` — blocked premium rate
   - Validates: partition extraction, description field, multiple partitions for CSS ordering

6. **Calling Search Spaces** (5 new + E911CSS existing)
   - `Standard-Employee-CSS` → Internal-PT(1), Local-PSTN-PT(2), LongDistance-PT(3), E911(4) — **4 partitions, ordered**
   - `Executive-CSS` → Internal-PT(1), Local-PSTN-PT(2), LongDistance-PT(3), International-PT(4), E911(5) — **5 partitions**
   - `Restricted-CSS` → Internal-PT(1), E911(2) — **minimal**
   - `Lobby-CSS` → Internal-PT(1), E911(2) — **same as Restricted but separate object**
   - `Line-CSS` → Internal-PT(1), Local-PSTN-PT(2) — **line-level CSS override test**
   - Validates: CSS member ordering (index field), 5-partition CSS, multiple CSSes sharing partitions, getCss member structure

### Phase 2: Lines and DNs (depend on partitions)

7. **Directory Numbers** (10 new)
   - `1001` in Internal-PT — John Doe primary
   - `1002` in Internal-PT — Jane Smith primary
   - `1003` in Internal-PT — Bob Wilson primary
   - `1004` in Internal-PT — Alice Chen primary (Branch)
   - `1005` in Internal-PT — admin-only user (no phone)
   - `1050` in Internal-PT — **shared team line** (on 3 devices)
   - `1051` in Internal-PT — **shared executive line** (on 2 devices)
   - `1099` in Internal-PT — lobby phone
   - `5001` in Internal-PT — hunt pilot DN
   - `5002` in Internal-PT — queue-style hunt pilot DN
   - Also: `7001`, `7002`, `7003` in Internal-PT — call park range
   - Also: `6001` in Internal-PT — CTI route point DN
   - Validates: DN extraction from phone lines, shared line detection (2-device and 3-device), DNs in partitions, DNs without partitions

### Phase 3: Users (depend on nothing, but device association comes later)

8. **End Users** (7 new)
   - `jdoe` — John Doe, jdoe@acme.com, Engineering dept, manager=msmith, CTI enabled, VM profile
   - `jsmith` — Jane Smith, jsmith@acme.com, Sales dept, CTI enabled, VM profile
   - `bwilson` — Bob Wilson, bwilson@acme.com, Engineering dept, manager=jdoe
   - `achen` — Alice Chen, achen@acme.com, Branch-Austin, no manager
   - `msmith` — Mike Smith (manager), msmith@acme.com, Engineering dept
   - `noemail` — Legacy User, **no mailid**, userid=legacyuser01, no VM
   - `adminonly` — Admin Account, admin@acme.com, **no associated devices**, no VM
   - Validates: user extraction, email/no-email edge case, manager field reference, CTI flag, associated devices (set in Phase 4), CSS on user, VM profile reference, user with no phone

### Phase 4: Phones and Device Associations (depend on users, pools, lines)

9. **Phones** (8-10 devices covering all scenarios)

   **User phones:**
   - `SEP001122334455` — already exists, Cisco 8845 SIP. **Assign to jdoe**, DP-HQ-Phones, Standard-Employee-CSS. **4 lines:** 1001(primary), 1050(shared team, index 2), 1051(shared exec, index 3), speed dial index 4. **Line-CSS on line 1.** e164Mask on line 1.
   - `SEP74A2E69EE6D0` — already exists, Cisco 8851 SIP. **Assign to jsmith**, DP-HQ-Phones, Standard-Employee-CSS. **2 lines:** 1002(primary), 1050(shared team, index 2).
   - `SEPBBCCDDEE1122` — new Cisco 7841 SIP. **Assign to bwilson**, DP-HQ-Phones, Standard-Employee-CSS. **2 lines:** 1003(primary), 1050(shared team, index 2). **7841 is "convertible" tier** — not native MPP but can be converted.
   - `SEPAABBCCDDEEFF` — new Cisco 8845 SIP. **Assign to achen**, DP-Branch-Phones, Standard-Employee-CSS. **1 line:** 1004.
   - `CSFjdoe` — new Jabber desktop (CSF prefix). **Assign to jdoe**, DP-HQ-Softphones, Standard-Employee-CSS. **1 line:** 1001 (same DN as desk phone — **shared line across device types**). Tests soft phone extraction and multi-device user.
   - `CSFjsmith` — new Jabber desktop. **Assign to jsmith**, DP-HQ-Softphones. **1 line:** 1002.

   **Common area phones:**
   - `ATA001144778888` — already exists, ATA 191 SIP. **No owner**, DP-CommonArea, Lobby-CSS. **1 line:** 1099. Common area + ATA (incompatible device type).
   - `AN0011223344080` — already exists, Analog Phone SCCP. **No owner**, Default pool. Tests SCCP protocol + analog model (incompatible).

   **Unprovisioned:**
   - `SEP112233445566` — new Cisco 8845 SIP. **No owner, no lines.** DP-HQ-Phones. Tests phone with no line appearances.

   Validates: multi-line phones (4 lines), shared lines (1050 on 3 devices, 1051 on 1+CSF), CSF prefix detection, ATA/analog device types, common area classification, ownerUserName populated vs null, line-level CSS, e164Mask, phone with no lines, device pool assignment, SCCP vs SIP protocol, device in multiple pools for same location

### Phase 5: Routing (depend on partitions, trunks)

10. **Route Group** (1)
    - `RG-PSTN-Primary` → contains `sip-trunk-to-lab-cucm` with priority 1
    - Validates: route_group_has_trunk cross-ref, member list extraction

11. **Route List** (1)
    - `RL-PSTN` → contains `RG-PSTN-Primary`
    - Validates: route_pattern_uses_route_list chain, route list member extraction

12. **Route Patterns** (4 new + 1 existing)
    - `9.1[2-9]XXXXXXXXX` in Local-PSTN-PT → RL-PSTN (local/national via route list)
    - `9.011!` in International-PT → RL-PSTN (international)
    - `9.1900XXXXXXX` in Block-Premium-PT → **blockEnable=true** (blocked pattern)
    - `0` in Internal-PT → direct to a trunk (operator pattern)
    - `911` in E911 → already exists
    - Validates: route pattern → partition cross-ref, route pattern → route list, block patterns, direct-to-trunk routing, digit manipulation masks

13. **Translation Patterns** (2)
    - `8XXX` in Internal-PT → calledPartyTransformationMask `+1408555XXXX` (4-digit → E.164)
    - `7X` in Internal-PT → calledPartyTransformationMask `170X` (short dial to 4-digit)
    - Validates: translation pattern extraction, mask fields, partition association

### Phase 6: Features (depend on lines, partitions)

14. **Hunt Group Chain — Standard** (hunt pilot + hunt list + line group)
    - Line Group `Sales-LG` → members: 1002 (jsmith), 1003 (bwilson)
    - Hunt List `Sales-HL` → algorithm: Top Down, references Sales-LG
    - Hunt Pilot `5001` in Internal-PT → references Sales-HL, forwardHuntNoAnswer to 1099, enabled, **not queue-style** (queueCalls disabled)
    - Validates: 3-object chain traversal, hunt_pilot_has_hunt_list, hunt_list_has_line_group, line_group_has_members, algorithm extraction, forwarding settings

15. **Hunt Group Chain — Queue-Style** (tests queue detection heuristics)
    - Line Group `Support-LG` → members: 1001 (jdoe), 1004 (achen)
    - Hunt List `Support-HL` → algorithm: Longest Idle, references Support-LG
    - Hunt Pilot `5002` in Internal-PT → references Support-HL, **queueCalls enabled**, maxCallersInQueue=10, MoH source set, overflowDestination=1099
    - Validates: queue-style detection heuristics (queueCalls, maxCallersInQueue, MoH), overflow routing

16. **CTI Route Point** (auto attendant proxy)
    - `CTIAA-MainMenu` → DP-HQ-Phones, Standard-Employee-CSS, 1 line with DN 6001 in Internal-PT
    - Validates: CTI RP extraction, line data on CTI RP, cti_rp_has_script cross-ref (even if script is null)

17. **Call Park Numbers** (3)
    - `7001`, `7002`, `7003` in Internal-PT
    - Validates: call park pattern extraction

18. **Pickup Group** (1)
    - `Engineering-Pickup` → members: 1001 (jdoe), 1003 (bwilson)
    - Validates: pickup group member list extraction

19. **Time Schedule + Time Periods** (1 schedule, 2 periods)
    - `Business-Hours-Period` → Mon-Fri 08:00-17:00
    - `After-Hours-Period` → Mon-Fri 17:00-08:00 (or Sat-Sun all day)
    - `Business-Hours-Schedule` → references both periods
    - Validates: schedule_has_time_period cross-ref, time period field extraction (startTime, endTime, dayOfWeek)

### Phase 7: Voicemail (depend on users)

20. **Voicemail Pilot** (1)
    - `8000` — pilot number for reaching voicemail
    - Validates: VM pilot extraction, dirn field

21. **Voicemail Profile association**
    - Associate existing `Default` VM profile with pilot `8000`
    - Set `voiceMailProfile=Default` on users: jdoe, jsmith, achen
    - Leave bwilson, noemail, adminonly WITHOUT voicemail
    - Validates: user → VM profile cross-ref, VM profile → pilot reference, users with/without VM

### Phase 8: User-Device Associations (final wiring)

22. **Associate devices to users**
    - jdoe → SEP001122334455, CSFjdoe (multi-device user)
    - jsmith → SEP74A2E69EE6D0, CSFjsmith
    - bwilson → SEPBBCCDDEE1122
    - achen → SEPAABBCCDDEEFF
    - Validates: user_has_device cross-ref, multi-device users, associatedDevices list extraction

23. **Set user CSSes**
    - jdoe → Executive-CSS (executive gets international)
    - jsmith → Standard-Employee-CSS
    - bwilson → Standard-Employee-CSS
    - achen → Standard-Employee-CSS
    - noemail → Restricted-CSS
    - Validates: user_has_css cross-ref

## Cross-Reference Coverage Matrix

After building, verify every one of the 27 cross-refs from 02-normalization-architecture.md has data:

| # | Relationship | Source in test data |
|---|---|---|
| 1 | device_pool_has_datetime_group | DP-HQ-Phones → DT-Eastern |
| 2 | device_pool_at_cucm_location | DP-HQ-Phones → HQ |
| 3 | user_has_device | jdoe → [SEP001122334455, CSFjdoe] |
| 4 | user_has_primary_dn | jdoe → 1001 |
| 5 | device_has_dn | SEP001122334455 → [1001, 1050, 1051] |
| 6 | dn_in_partition | 1001 → Internal-PT |
| 7 | device_in_pool | SEP001122334455 → DP-HQ-Phones |
| 8 | device_owned_by_user | SEP001122334455 → jdoe |
| 9 | common_area_device_in_pool | ATA001144778888 → DP-CommonArea |
| 10 | route_pattern_in_partition | 9.1[2-9]XX → Local-PSTN-PT |
| 11 | route_pattern_uses_gateway | 0 → sip-trunk (direct) |
| 12 | route_pattern_uses_route_list | 9.1[2-9]XX → RL-PSTN → RG-PSTN |
| 13 | route_group_has_trunk | RG-PSTN → sip-trunk |
| 14 | trunk_at_location | sip-trunk → Default pool → Hub_None |
| 15 | translation_pattern_in_partition | 8XXX → Internal-PT |
| 16 | css_contains_partition | Standard-Employee-CSS → [Internal(1), Local(2), LD(3), E911(4)] |
| 17 | partition_has_pattern | Internal-PT → [1001, 1002, ..., 5001, 5002, 7001-7003, 8XXX] |
| 18 | user_has_css | jdoe → Executive-CSS |
| 19 | device_has_css | SEP001122334455 → Standard-Employee-CSS |
| 20 | line_has_css | line 1 on SEP001122334455 → Line-CSS |
| 21 | hunt_pilot_has_hunt_list | 5001 → Sales-HL |
| 22 | hunt_list_has_line_group | Sales-HL → Sales-LG |
| 23 | line_group_has_members | Sales-LG → [1002, 1003] |
| 24 | cti_rp_has_script | CTIAA-MainMenu → (null/app ref) |
| 25 | schedule_has_time_period | Business-Hours-Schedule → [Business, After-Hours] |
| 26 | user_has_voicemail_profile | jdoe → Default |
| 27 | voicemail_profile_settings | Default → pilot 8000 |

## Validation After Build

Run each extractor against the live cluster and verify:
1. Object counts match expected
2. All relationship source data is present in extracted dicts
3. Shared line detector finds DN 1050 on 3 devices and DN 1051 on 2 devices
4. Workspace classifier identifies ATA and analog as common-area
5. CSS member ordering preserved for 4-partition and 5-partition CSSes
6. Hunt pilot chain fully traversable
7. User with no email has mailid=None
8. User with no phone has empty associatedDevices
9. Multi-device user has 2 entries in associatedDevices
10. Pagination works if we hit >200 of any object type (may need synthetic partitions)
