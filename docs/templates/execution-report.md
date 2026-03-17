# Execution Report: [OBJECTIVE_SUMMARY]

Executed: [YYYY-MM-DD HH:MM] ET
Agent: wxc-provision
Plan: [link or reference to deployment-plan.md used]

---

## 1. Summary

| Field | Value |
|-------|-------|
| Requested | [What the user asked for] |
| Executed | [What was actually done — may differ if partial failure] |
| Overall Status | **SUCCESS** / **PARTIAL** / **FAILED** |
| Steps Completed | [N] of [M] |
| Duration | [estimated wall-clock time] |

## 2. Results

Step-by-step outcome for every API call in the deployment plan.

| Step | Operation | Status | Resource ID | Notes |
|------|-----------|--------|------------|-------|
| 1 | [e.g., Create user Jane Smith] | SUCCESS | `Y2lzY29...` | Created in Austin location |
| 2 | [e.g., Assign Calling license] | SUCCESS | `license_id` | Professional license applied |
| 3 | [e.g., Assign phone number] | FAILED | -- | Error: no numbers available (see Errors) |
| 4 | [e.g., Configure voicemail] | SKIPPED | -- | Skipped: depends on Step 3 |

**Legend:** SUCCESS = completed as planned. FAILED = attempted, returned error. SKIPPED = not attempted due to dependency failure.

## 3. Resources Created/Modified

Final state of every resource touched during execution. Use this as the source of truth for what now exists.

| Resource Type | Name | ID | Status | Notes |
|--------------|------|-----|--------|-------|
| Person | Jane Smith | `Y2lzY29...` | Active | Calling license assigned |
| Phone Number | +1 (512) 555-0101 | `num_id` | Assigned | Bound to Jane Smith |
| Device | Cisco MPP 8845 | `device_id` | Updated | Shared line added |
| [etc.] | | | | |

## 4. Errors

Details on every failure encountered. Empty section if all steps succeeded.

| Step | Operation | Error Code | Error Message | Resolution |
|------|-----------|-----------|--------------|------------|
| 3 | Assign phone number | `404` | `Number not found in location pool` | Need to add numbers to Austin location first |
| [etc.] | | | | |

**Rollback performed:** [Yes — describe what was rolled back / No — partial success retained / N/A — no failures]

## 5. Verification

Confirmation checks the agent ran after execution to validate the deployment.

| Check | Method | Result |
|-------|--------|--------|
| User exists and is Calling-enabled | `webex_api.people.get(person_id)` | PASS |
| Phone number rings user | `webex_api.telephony.get_person(person_id)` | PASS |
| Voicemail configured | `webex_api.telephony.voicemail.read(person_id)` | PASS |
| Device registered | `webex_api.devices.get(device_id)` | FAIL — device offline |
| [Additional checks] | | |

## 6. Next Steps

What should happen after this deployment. Items marked with a person icon require manual action.

| # | Action | Owner | Notes |
|---|--------|-------|-------|
| 1 | [e.g., Test inbound call to +1 (512) 555-0101] | User | Verify ring and voicemail |
| 2 | [e.g., Configure receptionist client] | Agent | Run as follow-up deployment |
| 3 | [e.g., Retry failed number assignment] | Agent | Needs numbers added to pool first |
| 4 | [e.g., Share credentials with end users] | User | Portal access for self-service |
