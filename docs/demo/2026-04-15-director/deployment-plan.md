# Deployment Plan: CUCM Migration — director-demo-2026-04-15

Created: 2026-04-15
Agent: wxc-calling-builder

---

## 1. Objective

Migrate 300 users, 1100 devices, 4 workspaces, 71 call features from CUCM to Webex Calling (project: director-demo-2026-04-15).
6 locations, 17 trunks as routing infrastructure.

## 2. Prerequisites

| # | Prerequisite | Verification Method | Status |
|---|---|---|---|
| 1 | Webex org accessible | `wxcli whoami` | [ ] |
| 2 | Calling licenses available (300 Professional) | `wxcli licenses list` | [ ] |
| 3 | Number inventory for 6 location(s) | `wxcli numbers list --location-id ...` | [ ] |
| 4 | All decisions resolved (0 pending) | `wxcli cucm decisions --status pending` | [x] |

**Blockers found:** None

## 3. Resource Summary

| Resource Type | Count | Action |
|--------------|-------|--------|
| Device | 1100 | Create |
| Person | 300 | Create |
| Shared Line | 275 | Create |
| Pickup Group | 34 | Create |
| Hunt Group | 17 | Create |
| Translation Pattern | 17 | Create |
| Trunk | 17 | Create |
| Call Park | 12 | Create |
| Auto Attendant | 8 | Create |
| Route Group | 8 | Create |
| Operating Mode | 7 | Create |
| Location | 6 | Create |
| Workspace | 4 | Create |
| Calling Permission | 1 | Create |

## 4. Decisions Made

| ID | Type | Summary | Chosen Option |
|---|------|---------|---------------|
| D0365 | WORKSPACE_TYPE_UNCERTAIN | Common-area device 'dCloud_CER_P2' has ambiguous workspace classification — device pool '' does not clearly indicate room type | Accept fidelity loss |
| D0367 | WORKSPACE_SETTINGS_PROFESSIONAL_REQUIRED | Workspace 'dCloud CER Port 2' has voicemail settings that require Professional Workspace license | Accept fidelity loss |
| D0369 | WORKSPACE_SETTINGS_PROFESSIONAL_REQUIRED | Workspace 'Hotel Room 1100' has callForwarding settings that require Professional Workspace license | Accept fidelity loss |
| D0370 | WORKSPACE_TYPE_UNCERTAIN | Common-area device 'dCloud_CER_P3' has ambiguous workspace classification — device pool '' does not clearly indicate room type | Accept fidelity loss |
| D0372 | WORKSPACE_SETTINGS_PROFESSIONAL_REQUIRED | Workspace 'dCloud CER Port 3' has voicemail settings that require Professional Workspace license | Accept fidelity loss |
| D0373 | WORKSPACE_TYPE_UNCERTAIN | Common-area device 'dCloud_CER_P1' has ambiguous workspace classification — device pool '' does not clearly indicate room type | Accept fidelity loss |
| D0375 | WORKSPACE_SETTINGS_PROFESSIONAL_REQUIRED | Workspace 'dCloud CER Port 1' has voicemail settings that require Professional Workspace license | Accept fidelity loss |
| D0815 | FORWARDING_LOSSY | User 'mkumar' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0816 | FORWARDING_LOSSY | User 'amckenzie' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0817 | FORWARDING_LOSSY | User 'cholland' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0818 | FORWARDING_LOSSY | User 'smiller' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0819 | FORWARDING_LOSSY | User 'jli' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0820 | FORWARDING_LOSSY | User 'mcheng' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0821 | FORWARDING_LOSSY | User 'tbard' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0822 | FORWARDING_LOSSY | User 'aperez' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0823 | FORWARDING_LOSSY | User 'nfox' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0824 | FORWARDING_LOSSY | User 'wwhitman' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0825 | FORWARDING_LOSSY | User 'smacks' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0826 | FORWARDING_LOSSY | User 'chegarty' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0827 | FORWARDING_LOSSY | User 'kmelby' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0828 | FORWARDING_LOSSY | User 'bburke' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0829 | FORWARDING_LOSSY | User 'smckenna' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0830 | FORWARDING_LOSSY | User 'jxu' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0831 | FORWARDING_LOSSY | User 'dcebu' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0832 | FORWARDING_LOSSY | User 'fudinese' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0833 | FORWARDING_LOSSY | User 'blapointe' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0834 | FORWARDING_LOSSY | User 'mbrown' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0835 | FORWARDING_LOSSY | User 'rkhan' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0836 | FORWARDING_LOSSY | User 'jionello' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0837 | FORWARDING_LOSSY | User 'vkara' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0838 | FORWARDING_LOSSY | User 'adelamico' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0839 | FORWARDING_LOSSY | User 'mrossi' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0840 | FORWARDING_LOSSY | User 'avargas' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0841 | FORWARDING_LOSSY | User 'bstarr' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0842 | FORWARDING_LOSSY | User 'gstanislaus' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0843 | FORWARDING_LOSSY | User 'kfinney' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0844 | FORWARDING_LOSSY | User 'bgerman' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0845 | FORWARDING_LOSSY | User 'kadams' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0846 | FORWARDING_LOSSY | User 'rsmith' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0847 | FORWARDING_LOSSY | User 'msimek' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0848 | FORWARDING_LOSSY | User 'ribsen' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0849 | FORWARDING_LOSSY | User 'eyamadaya' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0850 | FORWARDING_LOSSY | User 'acassidy' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0851 | FORWARDING_LOSSY | User 'jweston' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0852 | FORWARDING_LOSSY | User 'pdudley' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0853 | FORWARDING_LOSSY | User 'cmccullen' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0854 | FORWARDING_LOSSY | User 'scentineo' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0855 | FORWARDING_LOSSY | User 'csinu' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0856 | FORWARDING_LOSSY | User 'cshor' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0857 | FORWARDING_LOSSY | User 'norr' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0858 | FORWARDING_LOSSY | User 'schristopolous' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0859 | FORWARDING_LOSSY | User 'gedwards' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0860 | FORWARDING_LOSSY | User 'sjones' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0861 | FORWARDING_LOSSY | User 'ffoster' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0862 | FORWARDING_LOSSY | User 'pseong' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0863 | FORWARDING_LOSSY | User 'akarlsson' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0864 | FORWARDING_LOSSY | User 'acondor' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0865 | FORWARDING_LOSSY | User 'amaguire' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D0866 | BUTTON_UNMAPPABLE | Template 'Cisco DX80 SIP' has 1 button(s) with no Webex equivalent: Redial (2 phones affected) | Accept loss |
| D0867 | BUTTON_UNMAPPABLE | Template 'Cisco DX70 SIP' has 1 button(s) with no Webex equivalent: Redial (2 phones affected) | Accept loss |
| D0868 | BUTTON_UNMAPPABLE | Template 'Cisco dCloud 8851 SIP' has 1 button(s) with no Webex equivalent: Hunt Group Logout (2 phones affected) | Accept loss |
| D0869 | BUTTON_UNMAPPABLE | Template 'Cisco dCloud DX650 SIP' has 1 button(s) with no Webex equivalent: Hunt Group Logout (2 phones affected) | Accept loss |
| D0870 | BUTTON_UNMAPPABLE | Template 'Cisco dCloud 8845 SIP' has 1 button(s) with no Webex equivalent: Hunt Group Logout (2 phones affected) | Accept loss |
| D0871 | BUTTON_UNMAPPABLE | Template 'Cisco dCloud 8865 SIP' has 1 button(s) with no Webex equivalent: Hunt Group Logout (2 phones affected) | Accept loss |
| D0940 | FEATURE_APPROXIMATION | Partition 'Directory URI' name suggests selective access (matched keyword 'direct'); CUCM caller-specific routing intent inferred from naming only | Configure Priority Alert post-migration |
| D0939 | FEATURE_APPROXIMATION | Partition 'E911' has 1 DN(s) and is reachable via only 1/9 CSSes (VIP/priority bypass pattern) | Configure Selective Accept post-migration |
| D0941 | FEATURE_APPROXIMATION | Partition 'Emergency_PT' name suggests selective access (matched keyword 'emergency'); CUCM caller-specific routing intent inferred from naming only | Configure Priority Alert post-migration |
| D0950 | ARCHITECTURE_ADVISORY | 1 device pools reference MRGLs — cloud handles media resources | Apply recommendation |
| D0946 | ARCHITECTURE_ADVISORY | 7 voicemail pilots can be eliminated — Webex uses per-user voicemail | Apply recommendation |
| D0943 | ARCHITECTURE_ADVISORY | 405 unknown phones need bulk replacement | Apply recommendation |
| D0956 | ARCHITECTURE_ADVISORY | 3 user/partition candidate(s) for Webex selective call handling — manual configuration | Apply recommendation |
| D0955 | ARCHITECTURE_ADVISORY | 56 Extension Mobility profiles — map to Webex hot desking | Apply recommendation |
| D0944 | ARCHITECTURE_ADVISORY | 4 trunks point to 198.18.135.54 — consolidate to one | Apply recommendation |
| D0954 | ARCHITECTURE_ADVISORY | 10 caller ID transformation patterns require manual review | Apply recommendation |
| D0942 | ARCHITECTURE_ADVISORY | 2 translation patterns duplicate Webex native digit normalization | Apply recommendation |
| D0948 | ARCHITECTURE_ADVISORY | PSTN recommendation: Local Gateway | Apply recommendation |
| D0952 | ARCHITECTURE_ADVISORY | 14 users have call recording enabled — enable Webex recording per-user during migration | Apply recommendation |
| D0951 | ARCHITECTURE_ADVISORY | E911 configuration detected — requires separate workstream | Apply recommendation |
| D0949 | ARCHITECTURE_ADVISORY | Dial plan style: hybrid (25% E.164) | Apply recommendation |
| D0945 | ARCHITECTURE_ADVISORY | 2 trunks point to 198.18.133.150 — consolidate to one | Apply recommendation |
| D0947 | ARCHITECTURE_ADVISORY | CPN transformations on 11 objects need flat Webex caller ID mapping | Apply recommendation |
| D0953 | ARCHITECTURE_ADVISORY | 55 remote destinations for 0 users — Webex SNR is simpler, manual setup required | Apply recommendation |

## 5. Batch Execution Order

| Tier | Batch | Operations | Resource Types |
|------|-------|------------|----------------|
| 0 | org-wide | 12 | Location |
| 1 | org-wide | 53 | line_key_template, Operating Mode, Route Group, route_list, Trunk |
| 2 | location:DP-ATL-Phones | 45 | Person |
| 2 | location:DP-CHI-Phones | 45 | Person |
| 2 | location:DP-DEN-Phones | 45 | Person |
| 2 | location:DP-NYC-Phones | 45 | Person |
| 2 | location:DP-SJC-Phones | 45 | Person |
| 2 | location:dCloud_DP | 52 | Person |
| 2 | org-wide | 4 | Workspace |
| 3 | location:DP-ATL-Phones | 140 | Device |
| 3 | location:DP-CHI-Phones | 140 | Device |
| 3 | location:DP-DEN-Phones | 140 | Device |
| 3 | location:DP-NYC-Phones | 140 | Device |
| 3 | location:DP-SJC-Phones | 140 | Device |
| 3 | location:dCloud_DP | 72 | Device |
| 3 | org-wide | 4 | Workspace |
| 4 | location:DP-ATL-Phones | 2 | Hunt Group |
| 4 | location:DP-CHI-Phones | 2 | Hunt Group |
| 4 | location:DP-DEN-Phones | 2 | Hunt Group |
| 4 | location:DP-NYC-Phones | 2 | Hunt Group |
| 4 | location:DP-SJC-Phones | 2 | Hunt Group |
| 4 | location:dCloud_DP | 7 | Hunt Group |
| 4 | org-wide | 25 | Auto Attendant, Pickup Group |
| 5 | location:DP-ATL-Phones | 46 | bulk_device_settings, ecbn_config |
| 5 | location:DP-CHI-Phones | 46 | bulk_device_settings, ecbn_config |
| 5 | location:DP-DEN-Phones | 46 | bulk_device_settings, ecbn_config |
| 5 | location:DP-NYC-Phones | 46 | bulk_device_settings, ecbn_config |
| 5 | location:DP-SJC-Phones | 46 | bulk_device_settings, ecbn_config |
| 5 | location:dCloud_DP | 105 | bulk_device_settings, ecbn_config, Person |
| 5 | org-wide | 83 | call_forwarding, Calling Permission, ecbn_config, Workspace |
| 6 | org-wide | 275 | Shared Line |
| 7 | location:dCloud_DP | 12 | bulk_line_key_template |
| 8 | location:DP-ATL-Phones | 1 | bulk_rebuild_phones |
| 8 | location:DP-CHI-Phones | 1 | bulk_rebuild_phones |
| 8 | location:DP-DEN-Phones | 1 | bulk_rebuild_phones |
| 8 | location:DP-NYC-Phones | 1 | bulk_rebuild_phones |
| 8 | location:DP-SJC-Phones | 1 | bulk_rebuild_phones |
| 8 | location:dCloud_DP | 1 | bulk_rebuild_phones |

## Activation Codes

The following firmware-convertible phones require an activation code
after their firmware is converted to MPP. Distribute the codes below
to on-site IT staff before the conversion window. Codes are generated
by `POST /v1/devices/activationCode` during execution.

| Device | Owner | Model | Code | Status |
|--------|-------|-------|------|--------|
| Alexander Bennett - X6121 - Cisco 8861 | Alexander Bennett | Cisco 8861 | (pending) | pending |
| Edward Turner - X5039 - Cisco 8832 | Edward Turner | Cisco 8832 | (pending) | pending |
| Nicole King - X3016 - Cisco 7841 | Nicole King | Cisco 7841 | (pending) | pending |
| Janet Ruiz - X6111 - Cisco 8845 | Janet Ruiz | Cisco 8845 | (pending) | pending |
| Jacob Edwards - X4034 - Cisco 8845 | Jacob Edwards | Cisco 8845 | (pending) | pending |
| Joshua Adams - X6104 - Cisco 7841 | Joshua Adams | Cisco 7841 | (pending) | pending |
| Samuel Collins - X3038 - Cisco 8861 | Samuel Collins | Cisco 8861 | (pending) | pending |
| George Kelly - X3020 - Cisco 8845 | George Kelly | Cisco 8845 | (pending) | pending |
| Brian Martin - X5012 - Cisco 8845 | Brian Martin | Cisco 8845 | (pending) | pending |
| Janet Collins - X3017 - Cisco 8861 | Janet Collins | Cisco 8861 | (pending) | pending |
| Charles Moore - X7012 - Cisco 8861 | Charles Moore | Cisco 8861 | (pending) | pending |
| Melissa Price - X6102 - Cisco 8845 | Melissa Price | Cisco 8845 | (pending) | pending |
| Betty Alvarez - X3008 - Cisco 8845 | Betty Alvarez | Cisco 8845 | (pending) | pending |
| Margaret Cruz - X4009 - Cisco 7821 | Margaret Cruz | Cisco 7821 | (pending) | pending |
| Emma Scott - X3010 - Cisco 7841 | Emma Scott | Cisco 7841 | (pending) | pending |
| Thomas Kelly - X7011 - Cisco 8861 | Thomas Kelly | Cisco 8861 | (pending) | pending |
| Charles Hughes - X3011 - Cisco 8845 | Charles Hughes | Cisco 8845 | (pending) | pending |
| Nicholas Mendoza - X7027 - Cisco 8832 | Nicholas Mendoza | Cisco 8832 | (pending) | pending |
| Brandon Garcia - X4033 - Cisco 7841 | Brandon Garcia | Cisco 7841 | (pending) | pending |
| Robert Young - X7001 - Cisco 8845 | Robert Young | Cisco 8845 | (pending) | pending |
| Charles Chavez - X7009 - Cisco 8861 | Charles Chavez | Cisco 8861 | (pending) | pending |
| Thomas Scott - X4040 - Cisco 7821 | Thomas Scott | Cisco 7821 | (pending) | pending |
| Donald Morgan - X4002 - Cisco 8861 | Donald Morgan | Cisco 8861 | (pending) | pending |
| Angela Murphy - X3044 - Cisco 7841 | Angela Murphy | Cisco 7841 | (pending) | pending |
| Kenneth King - X6133 - Cisco 8861 | Kenneth King | Cisco 8861 | (pending) | pending |
| Matthew Evans - X6142 - Cisco 7821 | Matthew Evans | Cisco 7821 | (pending) | pending |
| Samuel Scott - X7003 - Cisco 7841 | Samuel Scott | Cisco 7841 | (pending) | pending |
| Sandra Martinez - X7002 - Cisco 8832 | Sandra Martinez | Cisco 8832 | (pending) | pending |
| Jonathan Castillo - X5044 - Cisco 8861 | Jonathan Castillo | Cisco 8861 | (pending) | pending |
| Carol Scott - X3012 - Cisco 8861 | Carol Scott | Cisco 8861 | (pending) | pending |
| Thomas Patel - X4028 - Cisco 8845 | Thomas Patel | Cisco 8845 | (pending) | pending |
| Emma Gonzalez - X6103 - Cisco 7821 | Emma Gonzalez | Cisco 7821 | (pending) | pending |
| Janet Lewis - X5007 - Cisco 7841 | Janet Lewis | Cisco 7841 | (pending) | pending |
| Shirley Anderson - X4029 - Cisco 7841 | Shirley Anderson | Cisco 7841 | (pending) | pending |
| Shirley Campbell - X6101 - Cisco 7841 | Shirley Campbell | Cisco 7841 | (pending) | pending |
| Richard Diaz - X7038 - Cisco 7841 | Richard Diaz | Cisco 7841 | (pending) | pending |
| Donald Morgan - X4002 - Cisco 8861 | Donald Morgan | Cisco 8861 | (pending) | pending |
| Daniel Carter - X6108 - Cisco 8845 | Daniel Carter | Cisco 8845 | (pending) | pending |
| Kimberly Davis - X5028 - Cisco 7841 | Kimberly Davis | Cisco 7841 | (pending) | pending |
| Sharon Lee - X6110 - Cisco 7841 | Sharon Lee | Cisco 7841 | (pending) | pending |
| Charles Hughes - X3011 - Cisco 7821 | Charles Hughes | Cisco 7821 | (pending) | pending |
| Donald Hall - X6119 - Cisco 8845 | Donald Hall | Cisco 8845 | (pending) | pending |
| Nancy Richardson - X7021 - Cisco 7841 | Nancy Richardson | Cisco 7841 | (pending) | pending |
| Richard Kim - X5017 - Cisco 8861 | Richard Kim | Cisco 8861 | (pending) | pending |
| Christine Myers - X4004 - Cisco 7841 | Christine Myers | Cisco 7841 | (pending) | pending |
| William Robinson - X3023 - Cisco 8861 | William Robinson | Cisco 8861 | (pending) | pending |
| Gary Alvarez - X4037 - Cisco 8832 | Gary Alvarez | Cisco 8832 | (pending) | pending |
| Brian Allen - X6124 - Cisco 7821 | Brian Allen | Cisco 7821 | (pending) | pending |
| Daniel Stewart - X7029 - Cisco 7841 | Daniel Stewart | Cisco 7841 | (pending) | pending |
| Carolyn Green - X3036 - Cisco 8845 | Carolyn Green | Cisco 8845 | (pending) | pending |
| Catherine Bailey - X3040 - Cisco 7841 | Catherine Bailey | Cisco 7841 | (pending) | pending |
| Sandra Young - X5011 - Cisco 7841 | Sandra Young | Cisco 7841 | (pending) | pending |
| Jason Morgan - X5015 - Cisco 8861 | Jason Morgan | Cisco 8861 | (pending) | pending |
| Timothy Lee - X6135 - Cisco 7841 | Timothy Lee | Cisco 7841 | (pending) | pending |
| Raymond Robinson - X3022 - Cisco 8845 | Raymond Robinson | Cisco 8845 | (pending) | pending |
| Joshua Price - X5037 - Cisco 7821 | Joshua Price | Cisco 7821 | (pending) | pending |
| Stephen Nguyen - X3019 - Cisco 8845 | Stephen Nguyen | Cisco 8845 | (pending) | pending |
| Mark Evans - X5027 - Cisco 8861 | Mark Evans | Cisco 8861 | (pending) | pending |
| Carolyn Adams - X4042 - Cisco 8845 | Carolyn Adams | Cisco 8845 | (pending) | pending |
| Sarah Wood - X5004 - Cisco 7821 | Sarah Wood | Cisco 7821 | (pending) | pending |
| Barbara Morris - X7032 - Cisco 7841 | Barbara Morris | Cisco 7841 | (pending) | pending |
| Joshua Collins - X4034 - Cisco 7841 | Joshua Collins | Cisco 7841 | (pending) | pending |
| Kimberly Davis - X5028 - Cisco 7841 | Kimberly Davis | Cisco 7841 | (pending) | pending |
| Shirley Moore - X5001 - Cisco 7841 | Shirley Moore | Cisco 7841 | (pending) | pending |
| Scott Reed - X7016 - Cisco 7841 | Scott Reed | Cisco 7841 | (pending) | pending |
| Edward Martin - X5034 - Cisco 7841 | Edward Martin | Cisco 7841 | (pending) | pending |
| Gregory Castillo - X5009 - Cisco 8845 | Gregory Castillo | Cisco 8845 | (pending) | pending |
| Barbara Ramos - X3004 - Cisco 7841 | Barbara Ramos | Cisco 7841 | (pending) | pending |
| Scott Jones - X7020 - Cisco 8845 | Scott Jones | Cisco 8845 | (pending) | pending |
| Rebecca Wood - X4006 - Cisco 8861 | Rebecca Wood | Cisco 8861 | (pending) | pending |
| Gregory Wood - X7034 - Cisco 7841 | Gregory Wood | Cisco 7841 | (pending) | pending |
| Margaret Ross - X3013 - Cisco 7841 | Margaret Ross | Cisco 7841 | (pending) | pending |
| Debra James - X5003 - Cisco 7841 | Debra James | Cisco 7841 | (pending) | pending |
| Jason Howard - X3042 - Cisco 7841 | Jason Howard | Cisco 7841 | (pending) | pending |
| Sarah Wood - X5004 - Cisco 8845 | Sarah Wood | Cisco 8845 | (pending) | pending |
| Thomas Kelly - X7011 - Cisco 8832 | Thomas Kelly | Cisco 8832 | (pending) | pending |
| Mark Brooks - X6116 - Cisco 8861 | Mark Brooks | Cisco 8861 | (pending) | pending |
| Brian Chavez - X5032 - Cisco 7841 | Brian Chavez | Cisco 7841 | (pending) | pending |
| Debra James - X5003 - Cisco 7841 | Debra James | Cisco 7841 | (pending) | pending |
| Joshua Jackson - X5026 - Cisco 8845 | Joshua Jackson | Cisco 8845 | (pending) | pending |
| Debra Mitchell - X4011 - Cisco 7841 | Debra Mitchell | Cisco 7841 | (pending) | pending |
| Melissa Carter - X5001 - Cisco 8861 | Melissa Carter | Cisco 8861 | (pending) | pending |
| Emma Adams - X4026 - Cisco 7841 | Emma Adams | Cisco 7841 | (pending) | pending |
| Mark Moore - X3002 - Cisco 7821 | Mark Moore | Cisco 7821 | (pending) | pending |
| Robert Sanchez - X7026 - Cisco 7841 | Robert Sanchez | Cisco 7841 | (pending) | pending |
| Kathleen Clark - X7008 - Cisco 7841 | Kathleen Clark | Cisco 7841 | (pending) | pending |
| Joshua Jackson - X5026 - Cisco 8832 | Joshua Jackson | Cisco 8832 | (pending) | pending |
| Sandra Martinez - X7002 - Cisco 8845 | Sandra Martinez | Cisco 8845 | (pending) | pending |
| Jennifer Hughes - X7036 - Cisco 7821 | Jennifer Hughes | Cisco 7821 | (pending) | pending |
| Christopher Jimenez - X6100 - Cisco 7841 | Christopher Jimenez | Cisco 7841 | (pending) | pending |
| Richard Nelson - X6141 - Cisco 8845 | Richard Nelson | Cisco 8845 | (pending) | pending |
| Mary Rivera - X4025 - Cisco 7841 | Mary Rivera | Cisco 7841 | (pending) | pending |
| Ronald Scott - X4013 - Cisco 7821 | Ronald Scott | Cisco 7821 | (pending) | pending |
| George Cox - X7005 - Cisco 8845 | George Cox | Cisco 8845 | (pending) | pending |
| Tanya Adams - 8861 MRA - X6024 | Tanya Adams | Cisco 8861 | (pending) | pending |
| Tanya Adams - 8845 MRA - X6024 | Tanya Adams | Cisco 8845 | (pending) | pending |
| Tanya Adams - 8865 MRA - X6024 | Tanya Adams | Cisco 8865 | (pending) | pending |
| Tanya Adams - 8841 MRA - X6024 | Tanya Adams | Cisco 8841 | (pending) | pending |
| Tanya Adams - 8851 MRA - X6024 | Tanya Adams | Cisco 8851 | (pending) | pending |
| Janet Lewis - X5007 - Cisco 8845 | Janet Lewis | Cisco 8845 | (pending) | pending |
| Alexander Rodriguez - X3021 - Cisco 7841 | Alexander Rodriguez | Cisco 7841 | (pending) | pending |
| Anthony Ramos - X4019 - Cisco 8845 | Anthony Ramos | Cisco 8845 | (pending) | pending |
| Betty Alvarez - X3008 - Cisco 8861 | Betty Alvarez | Cisco 8861 | (pending) | pending |
| Jonathan Castillo - X5044 - Cisco 8861 | Jonathan Castillo | Cisco 8861 | (pending) | pending |
| Emma Patel - X5029 - Cisco 7841 | Emma Patel | Cisco 7841 | (pending) | pending |
| Donald Morgan - X4002 - Cisco 8845 | Donald Morgan | Cisco 8845 | (pending) | pending |
| Kevin Myers - X6118 - Cisco 8861 | Kevin Myers | Cisco 8861 | (pending) | pending |
| Janet Ruiz - X6111 - Cisco 7841 | Janet Ruiz | Cisco 7841 | (pending) | pending |
| Ashley Allen - X5041 - Cisco 8861 | Ashley Allen | Cisco 8861 | (pending) | pending |
| Daniel King - X4027 - Cisco 7821 | Daniel King | Cisco 7821 | (pending) | pending |
| Sharon Lee - X6140 - Cisco 7841 | Sharon Lee | Cisco 7841 | (pending) | pending |
| Angela Ramos - X4031 - Cisco 8845 | Angela Ramos | Cisco 8845 | (pending) | pending |
| Scott Ortiz - X4043 - Cisco 7821 | Scott Ortiz | Cisco 7821 | (pending) | pending |
| Dorothy Myers - X3041 - Cisco 8845 | Dorothy Myers | Cisco 8845 | (pending) | pending |
| Charles Edwards - X6131 - Cisco 7841 | Charles Edwards | Cisco 7841 | (pending) | pending |
| Emma Gonzalez - X6103 - Cisco 8845 | Emma Gonzalez | Cisco 8845 | (pending) | pending |
| Rachel Kelly - X6113 - Cisco 7821 | Rachel Kelly | Cisco 7821 | (pending) | pending |
| Raymond Torres - X7017 - Cisco 8861 | Raymond Torres | Cisco 8861 | (pending) | pending |
| Jason Howard - X3042 - Cisco 7841 | Jason Howard | Cisco 7841 | (pending) | pending |
| Christopher Taylor - X4022 - Cisco 7841 | Christopher Taylor | Cisco 7841 | (pending) | pending |
| Katherine Murphy - X3037 - Cisco 8832 | Katherine Murphy | Cisco 8832 | (pending) | pending |
| Sharon Lee - X6140 - Cisco 8861 | Sharon Lee | Cisco 8861 | (pending) | pending |
| Melissa Carter - X5001 - Cisco 8861 | Melissa Carter | Cisco 8861 | (pending) | pending |
| Kathleen Clark - X7008 - Cisco 8845 | Kathleen Clark | Cisco 8845 | (pending) | pending |
| Jennifer Jones - X4000 - Cisco 8832 | Jennifer Jones | Cisco 8832 | (pending) | pending |
| Shirley Moore - X5040 - Cisco 8845 | Shirley Moore | Cisco 8845 | (pending) | pending |
| Melissa Carter - X5001 - Cisco 8845 | Melissa Carter | Cisco 8845 | (pending) | pending |
| Anthony Ramos - X4019 - Cisco 8845 | Anthony Ramos | Cisco 8845 | (pending) | pending |
| Patrick Sanders - X6143 - Cisco 8845 | Patrick Sanders | Cisco 8845 | (pending) | pending |
| Edward Martin - X5034 - Cisco 7821 | Edward Martin | Cisco 7821 | (pending) | pending |
| Matthew Evans - X6142 - Cisco 8861 | Matthew Evans | Cisco 8861 | (pending) | pending |
| Richard Diaz - X7038 - Cisco 7821 | Richard Diaz | Cisco 7821 | (pending) | pending |
| Nicole Green - X6115 - Cisco 8861 | Nicole Green | Cisco 8861 | (pending) | pending |
| Laura Mitchell - X5043 - Cisco 7841 | Laura Mitchell | Cisco 7841 | (pending) | pending |
| Jennifer Jones - X4000 - Cisco 7841 | Jennifer Jones | Cisco 7841 | (pending) | pending |
| Jennifer Hughes - X7036 - Cisco 8845 | Jennifer Hughes | Cisco 8845 | (pending) | pending |
| Laura Mitchell - X5043 - Cisco 7841 | Laura Mitchell | Cisco 7841 | (pending) | pending |
| Susan Lopez - X3014 - Cisco 8845 | Susan Lopez | Cisco 8845 | (pending) | pending |
| Monica Cheng - 8861 MRA - X6020 | Monica Cheng | Cisco 8861 | (pending) | pending |
| Monica Cheng - 8845 MRA - X6020 | Monica Cheng | Cisco 8845 | (pending) | pending |
| Monica Cheng - 8865 MRA - X6020 | Monica Cheng | Cisco 8865 | (pending) | pending |
| Monica Cheng - 8841 MRA - X6020 | Monica Cheng | Cisco 8841 | (pending) | pending |
| Monica Cheng - 8851 MRA - X6020 | Monica Cheng | Cisco 8851 | (pending) | pending |
| Anthony Young - X6123 - Cisco 8861 | Anthony Young | Cisco 8861 | (pending) | pending |
| Richard Diaz - X7038 - Cisco 8861 | Richard Diaz | Cisco 8861 | (pending) | pending |
| Brian Allen - X6124 - Cisco 8861 | Brian Allen | Cisco 8861 | (pending) | pending |
| Ashley Patel - X5019 - Cisco 7841 | Ashley Patel | Cisco 7841 | (pending) | pending |
| Christopher Jimenez - X6131 - Cisco 8845 | Christopher Jimenez | Cisco 8845 | (pending) | pending |
| Samantha Howard - X4041 - Cisco 8845 | Samantha Howard | Cisco 8845 | (pending) | pending |
| Deborah Collins - X4003 - Cisco 8861 | Deborah Collins | Cisco 8861 | (pending) | pending |
| Scott Jackson - X7031 - Cisco 7821 | Scott Jackson | Cisco 7821 | (pending) | pending |
| Ashley Taylor - X4017 - Cisco 8845 | Ashley Taylor | Cisco 8845 | (pending) | pending |
| Kathleen Gray - X7007 - Cisco 7821 | Kathleen Gray | Cisco 7821 | (pending) | pending |
| Sarah Cruz - X7001 - Cisco 7821 | Sarah Cruz | Cisco 7821 | (pending) | pending |
| Nicholas Long - X7031 - Cisco 7821 | Nicholas Long | Cisco 7821 | (pending) | pending |
| Angela Ramos - X4031 - Cisco 8832 | Angela Ramos | Cisco 8832 | (pending) | pending |
| Kevin Myers - X6118 - Cisco 7821 | Kevin Myers | Cisco 7821 | (pending) | pending |
| George Lewis - X3043 - Cisco 7841 | George Lewis | Cisco 7841 | (pending) | pending |
| Joshua Collins - X4034 - Cisco 8845 | Joshua Collins | Cisco 8845 | (pending) | pending |
| Samantha Anderson - X3000 - Cisco 8845 | Samantha Anderson | Cisco 8845 | (pending) | pending |
| Timothy Gonzalez - X6129 - Cisco 8845 | Timothy Gonzalez | Cisco 8845 | (pending) | pending |
| Brandon Foster - X5032 - Cisco 8845 | Brandon Foster | Cisco 8845 | (pending) | pending |
| Elizabeth Baker - X6134 - Cisco 7841 | Elizabeth Baker | Cisco 7841 | (pending) | pending |
| Anna Evans - X7041 - Cisco 7841 | Anna Evans | Cisco 7841 | (pending) | pending |
| Stephen Nguyen - X3019 - Cisco 8845 | Stephen Nguyen | Cisco 8845 | (pending) | pending |
| Stephen Lopez - X6136 - Cisco 7821 | Stephen Lopez | Cisco 7821 | (pending) | pending |
| Jennifer Kelly - X7013 - Cisco 8845 | Jennifer Kelly | Cisco 8845 | (pending) | pending |
| Eric Smith - X7044 - Cisco 7841 | Eric Smith | Cisco 7841 | (pending) | pending |
| Ronald Ortiz - X5006 - Cisco 7841 | Ronald Ortiz | Cisco 7841 | (pending) | pending |
| Jason Howard - X3042 - Cisco 7821 | Jason Howard | Cisco 7821 | (pending) | pending |
| Lisa Evans - X6127 - Cisco 7841 | Lisa Evans | Cisco 7841 | (pending) | pending |
| Ronald Scott - X4013 - Cisco 7821 | Ronald Scott | Cisco 7821 | (pending) | pending |
| Kimberly Jones - X4008 - Cisco 7821 | Kimberly Jones | Cisco 7821 | (pending) | pending |
| Richard Nelson - X6141 - Cisco 8832 | Richard Nelson | Cisco 8832 | (pending) | pending |
| Anthony Rodriguez - X4018 - Cisco 8832 | Anthony Rodriguez | Cisco 8832 | (pending) | pending |
| Robert Miller - X4016 - Cisco 8845 | Robert Miller | Cisco 8845 | (pending) | pending |
| Deborah Collins - X4003 - Cisco 8845 | Deborah Collins | Cisco 8845 | (pending) | pending |
| Susan Lopez - X3014 - Cisco 8845 | Susan Lopez | Cisco 8845 | (pending) | pending |
| Jacob Walker - X5036 - Cisco 7841 | Jacob Walker | Cisco 7841 | (pending) | pending |
| Daniel King - X4027 - Cisco 8845 | Daniel King | Cisco 8845 | (pending) | pending |
| Frank Ward - X6108 - Cisco 8845 | Frank Ward | Cisco 8845 | (pending) | pending |
| Timothy Hall - X6128 - Cisco 7841 | Timothy Hall | Cisco 7841 | (pending) | pending |
| Richard Kim - X5017 - Cisco 8845 | Richard Kim | Cisco 8845 | (pending) | pending |
| Charles Hughes - X3011 - Cisco 7821 | Charles Hughes | Cisco 7821 | (pending) | pending |
| Emma Adams - X4026 - Cisco 7821 | Emma Adams | Cisco 7821 | (pending) | pending |
| Ashley Allen - X5041 - Cisco 8845 | Ashley Allen | Cisco 8845 | (pending) | pending |
| Nicole Smith - X7000 - Cisco 8845 | Nicole Smith | Cisco 8845 | (pending) | pending |
| Gary Alvarez - X4037 - Cisco 8832 | Gary Alvarez | Cisco 8832 | (pending) | pending |
| Raymond Ramirez - X4015 - Cisco 7841 | Raymond Ramirez | Cisco 7841 | (pending) | pending |
| Edward Turner - X5039 - Cisco 8861 | Edward Turner | Cisco 8861 | (pending) | pending |
| Nancy Gutierrez - X7031 - Cisco 8861 | Nancy Gutierrez | Cisco 8861 | (pending) | pending |
| Daniel Price - X6107 - Cisco 7841 | Daniel Price | Cisco 7841 | (pending) | pending |
| Linda Perez - X7014 - Cisco 7821 | Linda Perez | Cisco 7821 | (pending) | pending |
| Emma Scott - X3010 - Cisco 7821 | Emma Scott | Cisco 7821 | (pending) | pending |
| Robert Miller - X4016 - Cisco 8845 | Robert Miller | Cisco 8845 | (pending) | pending |
| Linda Perez - X7014 - Cisco 8845 | Linda Perez | Cisco 8845 | (pending) | pending |
| Jack Scott - X3001 - Cisco 8861 | Jack Scott | Cisco 8861 | (pending) | pending |
| Shirley Campbell - X6101 - Cisco 8845 | Shirley Campbell | Cisco 8845 | (pending) | pending |
| Samuel Scott - X7003 - Cisco 7841 | Samuel Scott | Cisco 7841 | (pending) | pending |
| Nicholas Long - X7031 - Cisco 8832 | Nicholas Long | Cisco 8832 | (pending) | pending |
| Karen White - X7004 - Cisco 7841 | Karen White | Cisco 7841 | (pending) | pending |
| David Ramirez - X3035 - Cisco 7841 | David Ramirez | Cisco 7841 | (pending) | pending |
| Barbara Ramos - X3004 - Cisco 7841 | Barbara Ramos | Cisco 7841 | (pending) | pending |
| Nicole Smith - X7009 - Cisco 7821 | Nicole Smith | Cisco 7821 | (pending) | pending |
| Alexander Bennett - X6121 - Cisco 8845 | Alexander Bennett | Cisco 8845 | (pending) | pending |
| Joshua Jackson - X5026 - Cisco 7841 | Joshua Jackson | Cisco 7841 | (pending) | pending |
| John Brown - X3005 - Cisco 7841 | John Brown | Cisco 7841 | (pending) | pending |
| Sarah Cruz - X7001 - Cisco 8845 | Sarah Cruz | Cisco 8845 | (pending) | pending |
| William Torres - X7040 - Cisco 8845 | William Torres | Cisco 8845 | (pending) | pending |
| Ashley Allen - X5041 - Cisco 8861 | Ashley Allen | Cisco 8861 | (pending) | pending |
| Dorothy Myers - X3041 - Cisco 8845 | Dorothy Myers | Cisco 8845 | (pending) | pending |
| Sandra Nelson - X4001 - Cisco 7841 | Sandra Nelson | Cisco 7841 | (pending) | pending |
| Mary Rivera - X4025 - Cisco 8845 | Mary Rivera | Cisco 8845 | (pending) | pending |
| Steven Thompson - X4023 - Cisco 7821 | Steven Thompson | Cisco 7821 | (pending) | pending |
| Daniel King - X4027 - Cisco 8861 | Daniel King | Cisco 8861 | (pending) | pending |
| Susan Murphy - X6117 - Cisco 8832 | Susan Murphy | Cisco 8832 | (pending) | pending |
| Jacob Edwards - X4030 - Cisco 8861 | Jacob Edwards | Cisco 8861 | (pending) | pending |
| Samuel Collins - X3038 - Cisco 8845 | Samuel Collins | Cisco 8845 | (pending) | pending |
| Pamela Gutierrez - X7043 - Cisco 7841 | Pamela Gutierrez | Cisco 7841 | (pending) | pending |
| Samuel Scott - X7003 - Cisco 7841 | Samuel Scott | Cisco 7841 | (pending) | pending |
| Sandra Sanders - X5023 - Cisco 8845 | Sandra Sanders | Cisco 8845 | (pending) | pending |
| David Robinson - X7024 - Cisco 7841 | David Robinson | Cisco 7841 | (pending) | pending |
| Eric Smith - X7044 - Cisco 8845 | Eric Smith | Cisco 8845 | (pending) | pending |
| Sarah Cook - X5022 - Cisco 7841 | Sarah Cook | Cisco 7841 | (pending) | pending |
| Christine Myers - X4004 - Cisco 7821 | Christine Myers | Cisco 7821 | (pending) | pending |
| Brandon Foster - X5015 - Cisco 7841 | Brandon Foster | Cisco 7841 | (pending) | pending |
| Jason Morgan - X5010 - Cisco 7841 | Jason Morgan | Cisco 7841 | (pending) | pending |
| Matthew Smith - X7042 - Cisco 8845 | Matthew Smith | Cisco 8845 | (pending) | pending |
| Scott Smith - X4021 - Cisco 7821 | Scott Smith | Cisco 7821 | (pending) | pending |
| Scott Ortiz - X4043 - Cisco 8845 | Scott Ortiz | Cisco 8845 | (pending) | pending |
| Christine Myers - X4004 - Cisco 7841 | Christine Myers | Cisco 7841 | (pending) | pending |
| Nicole Brooks - X3028 - Cisco 8845 | Nicole Brooks | Cisco 8845 | (pending) | pending |
| Nancy Richardson - X7021 - Cisco 7821 | Nancy Richardson | Cisco 7821 | (pending) | pending |
| Melissa Rivera - X3026 - Cisco 8845 | Melissa Rivera | Cisco 8845 | (pending) | pending |
| Pamela Wood - X6130 - Cisco 8832 | Pamela Wood | Cisco 8832 | (pending) | pending |
| Charles Reyes - X3030 - Cisco 7841 | Charles Reyes | Cisco 7841 | (pending) | pending |
| Brenda Murphy - X5031 - Cisco 8845 | Brenda Murphy | Cisco 8845 | (pending) | pending |
| Nicole Cooper - X7033 - Cisco 8845 | Nicole Cooper | Cisco 8845 | (pending) | pending |
| Deborah Taylor - X7025 - Cisco 8845 | Deborah Taylor | Cisco 8845 | (pending) | pending |
| Carolyn Green - X3036 - Cisco 8845 | Carolyn Green | Cisco 8845 | (pending) | pending |
| Scott Smith - X4021 - Cisco 8861 | Scott Smith | Cisco 8861 | (pending) | pending |
| Patrick Smith - X6125 - Cisco 8832 | Patrick Smith | Cisco 8832 | (pending) | pending |
| Debra James - X5003 - Cisco 8845 | Debra James | Cisco 8845 | (pending) | pending |
| Cynthia Davis - X5038 - Cisco 8861 | Cynthia Davis | Cisco 8861 | (pending) | pending |
| Margaret Robinson - X3006 - Cisco 8845 | Margaret Robinson | Cisco 8845 | (pending) | pending |
| Elizabeth Hernandez - X4038 - Cisco 8861 | Elizabeth Hernandez | Cisco 8861 | (pending) | pending |
| Benjamin Gray - X5014 - Cisco 8832 | Benjamin Gray | Cisco 8832 | (pending) | pending |
| Kimberly Davis - X5028 - Cisco 7821 | Kimberly Davis | Cisco 7821 | (pending) | pending |
| Gary Ward - X4007 - Cisco 7821 | Gary Ward | Cisco 7821 | (pending) | pending |
| Elizabeth Baker - X6134 - Cisco 7821 | Elizabeth Baker | Cisco 7821 | (pending) | pending |
| Janet Collins - X3017 - Cisco 7841 | Janet Collins | Cisco 7841 | (pending) | pending |
| Timothy Scott - X3024 - Cisco 8845 | Timothy Scott | Cisco 8845 | (pending) | pending |
| Laura Kim - X5018 - Cisco 8845 | Laura Kim | Cisco 8845 | (pending) | pending |
| Sandra Sanders - X5023 - Cisco 8832 | Sandra Sanders | Cisco 8832 | (pending) | pending |
| Emma Scott - X3006 - Cisco 8845 | Emma Scott | Cisco 8845 | (pending) | pending |
| Thomas Thompson - X6112 - Cisco 7841 | Thomas Thompson | Cisco 7841 | (pending) | pending |
| Jessica Collins - X4014 - Cisco 8845 | Jessica Collins | Cisco 8845 | (pending) | pending |
| Anthony Rodriguez - X4018 - Cisco 7821 | Anthony Rodriguez | Cisco 7821 | (pending) | pending |
| Debra James - X5003 - Cisco 8845 | Debra James | Cisco 8845 | (pending) | pending |
| Rebecca Nelson - X7006 - Cisco 8845 | Rebecca Nelson | Cisco 8845 | (pending) | pending |
| Amy Anderson - X4001 - Cisco 7841 | Amy Anderson | Cisco 7841 | (pending) | pending |
| Laura Mitchell - X5043 - Cisco 8845 | Laura Mitchell | Cisco 8845 | (pending) | pending |
| Anna Ramirez - X5021 - Cisco 7821 | Anna Ramirez | Cisco 7821 | (pending) | pending |
| Gregory Adams - X5025 - Cisco 8832 | Gregory Adams | Cisco 8832 | (pending) | pending |
| Kevin Chavez - X5042 - Cisco 8845 | Kevin Chavez | Cisco 8845 | (pending) | pending |
| Donald Clark - X5016 - Cisco 8861 | Donald Clark | Cisco 8861 | (pending) | pending |
| Daniel Carter - X6110 - Cisco 8845 | Daniel Carter | Cisco 8845 | (pending) | pending |
| Margaret Ross - X3013 - Cisco 7841 | Margaret Ross | Cisco 7841 | (pending) | pending |
| Jessica Carter - X3018 - Cisco 8832 | Jessica Carter | Cisco 8832 | (pending) | pending |
| David Robinson - X7024 - Cisco 8861 | David Robinson | Cisco 8861 | (pending) | pending |
| Jack Scott - X3001 - Cisco 7841 | Jack Scott | Cisco 7841 | (pending) | pending |
| Nicole Jackson - X4039 - Cisco 8861 | Nicole Jackson | Cisco 8861 | (pending) | pending |
| Katherine Murphy - X3037 - Cisco 8861 | Katherine Murphy | Cisco 8861 | (pending) | pending |
| Janet Collins - X3017 - Cisco 8832 | Janet Collins | Cisco 8832 | (pending) | pending |
| Anthony Young - X6123 - Cisco 8845 | Anthony Young | Cisco 8845 | (pending) | pending |
| Jessica Collins - X4014 - Cisco 7821 | Jessica Collins | Cisco 7821 | (pending) | pending |
| Amy Anderson - X4001 - Cisco 7841 | Amy Anderson | Cisco 7841 | (pending) | pending |
| Mark Mendoza - X3032 - Cisco 8861 | Mark Mendoza | Cisco 8861 | (pending) | pending |
| Katherine Perez - X6139 - Cisco 7821 | Katherine Perez | Cisco 7821 | (pending) | pending |
| Timothy Lee - X6135 - Cisco 7841 | Timothy Lee | Cisco 7841 | (pending) | pending |
| Matthew Smith - X7042 - Cisco 7841 | Matthew Smith | Cisco 7841 | (pending) | pending |
| Amy Anderson - X4001 - Cisco 8861 | Amy Anderson | Cisco 8861 | (pending) | pending |
| William Torres - X7035 - Cisco 8861 | William Torres | Cisco 8861 | (pending) | pending |
| Brandon Garcia - X4033 - Cisco 8861 | Brandon Garcia | Cisco 8861 | (pending) | pending |
| Samantha Morales - X6106 - Cisco 7821 | Samantha Morales | Cisco 7821 | (pending) | pending |
| Donald Clark - X5016 - Cisco 7841 | Donald Clark | Cisco 7841 | (pending) | pending |
| Timothy Gonzalez - X6129 - Cisco 7841 | Timothy Gonzalez | Cisco 7841 | (pending) | pending |
| Nicole Brown - X3007 - Cisco 8845 | Nicole Brown | Cisco 8845 | (pending) | pending |
| Nicole Jackson - X4039 - Cisco 8861 | Nicole Jackson | Cisco 8861 | (pending) | pending |
| Samuel Sanders - X5000 - Cisco 8861 | Samuel Sanders | Cisco 8861 | (pending) | pending |
| Stephen Lopez - X6136 - Cisco 8845 | Stephen Lopez | Cisco 8845 | (pending) | pending |
| Cynthia Davis - X5038 - Cisco 7821 | Cynthia Davis | Cisco 7821 | (pending) | pending |
| Christine Wright - X3027 - Cisco 8845 | Christine Wright | Cisco 8845 | (pending) | pending |
| Dorothy Moore - X3039 - Cisco 7821 | Dorothy Moore | Cisco 7821 | (pending) | pending |
| Samantha Morales - X6106 - Cisco 8832 | Samantha Morales | Cisco 8832 | (pending) | pending |
| Deborah Cruz - X6126 - Cisco 8845 | Deborah Cruz | Cisco 8845 | (pending) | pending |
| Janet Lewis - X5007 - Cisco 7841 | Janet Lewis | Cisco 7841 | (pending) | pending |
| Robert Hill - X5008 - Cisco 7821 | Robert Hill | Cisco 7821 | (pending) | pending |
| Samantha Anderson - X3000 - Cisco 8861 | Samantha Anderson | Cisco 8861 | (pending) | pending |
| Anthony Young - X6123 - Cisco 7821 | Anthony Young | Cisco 7821 | (pending) | pending |
| Emma Adams - X4026 - Cisco 8845 | Emma Adams | Cisco 8845 | (pending) | pending |
| Richard Nelson - X6141 - Cisco 7841 | Richard Nelson | Cisco 7841 | (pending) | pending |
| Sandra Martinez - X7002 - Cisco 8845 | Sandra Martinez | Cisco 8845 | (pending) | pending |
| Jonathan Castillo - X5044 - Cisco 8861 | Jonathan Castillo | Cisco 8861 | (pending) | pending |
| Linda Morris - X4035 - Cisco 7821 | Linda Morris | Cisco 7821 | (pending) | pending |
| Elizabeth Hernandez - X4038 - Cisco 8845 | Elizabeth Hernandez | Cisco 8845 | (pending) | pending |
| Nicole Brown - X3007 - Cisco 8845 | Nicole Brown | Cisco 8845 | (pending) | pending |
| Samuel Scott - X7003 - Cisco 8845 | Samuel Scott | Cisco 8845 | (pending) | pending |
| Sarah Wood - X5004 - Cisco 8832 | Sarah Wood | Cisco 8832 | (pending) | pending |
| George Kelly - X3020 - Cisco 8845 | George Kelly | Cisco 8845 | (pending) | pending |
| Christopher Jimenez - X6100 - Cisco 8845 | Christopher Jimenez | Cisco 8845 | (pending) | pending |
| Richard Kim - X5017 - Cisco 8832 | Richard Kim | Cisco 8832 | (pending) | pending |
| Mark Moore - X3002 - Cisco 8845 | Mark Moore | Cisco 8845 | (pending) | pending |
| Laura Cook - X4032 - Cisco 8861 | Laura Cook | Cisco 8861 | (pending) | pending |
| Charles Edwards - X6131 - Cisco 7841 | Charles Edwards | Cisco 7841 | (pending) | pending |
| Frank Ward - X6108 - Cisco 7821 | Frank Ward | Cisco 7821 | (pending) | pending |
| Carolyn Green - X3036 - Cisco 8845 | Carolyn Green | Cisco 8845 | (pending) | pending |
| Stephen Lopez - X6136 - Cisco 8845 | Stephen Lopez | Cisco 8845 | (pending) | pending |
| Patrick Smith - X6125 - Cisco 7841 | Patrick Smith | Cisco 7841 | (pending) | pending |
| Jacob Morris - X7019 - Cisco 8845 | Jacob Morris | Cisco 8845 | (pending) | pending |
| Angela Murphy - X3044 - Cisco 7821 | Angela Murphy | Cisco 7821 | (pending) | pending |
| Katherine Murphy - X3037 - Cisco 8845 | Katherine Murphy | Cisco 8845 | (pending) | pending |
| Donald Campbell - X4010 - Cisco 8845 | Donald Campbell | Cisco 8845 | (pending) | pending |
| Barbara Morris - X7032 - Cisco 8861 | Barbara Morris | Cisco 8861 | (pending) | pending |
| Sandra Nelson - X4020 - Cisco 8845 | Sandra Nelson | Cisco 8845 | (pending) | pending |
| Anna Evans - X7041 - Cisco 7841 | Anna Evans | Cisco 7841 | (pending) | pending |
| Frank Ward - X6108 - Cisco 8861 | Frank Ward | Cisco 8861 | (pending) | pending |
| Lisa Brooks - X6120 - Cisco 8832 | Lisa Brooks | Cisco 8832 | (pending) | pending |
| Rebecca Wood - X4006 - Cisco 8845 | Rebecca Wood | Cisco 8845 | (pending) | pending |
| Ryan Kim - X7023 - Cisco 7841 | Ryan Kim | Cisco 7841 | (pending) | pending |
| Anthony Rodriguez - X4018 - Cisco 7841 | Anthony Rodriguez | Cisco 7841 | (pending) | pending |
| Shirley Campbell - X6101 - Cisco 8845 | Shirley Campbell | Cisco 8845 | (pending) | pending |
| David Ramirez - X3005 - Cisco 7821 | David Ramirez | Cisco 7821 | (pending) | pending |
| Laura Kim - X5018 - Cisco 7841 | Laura Kim | Cisco 7841 | (pending) | pending |
| Timothy Hall - X6128 - Cisco 7821 | Timothy Hall | Cisco 7821 | (pending) | pending |
| Steven Morris - X7039 - Cisco 7841 | Steven Morris | Cisco 7841 | (pending) | pending |
| William Torres - X7040 - Cisco 8861 | William Torres | Cisco 8861 | (pending) | pending |
| Deborah Collins - X4003 - Cisco 7821 | Deborah Collins | Cisco 7821 | (pending) | pending |
| Rachel Kelly - X6113 - Cisco 7841 | Rachel Kelly | Cisco 7841 | (pending) | pending |
| Raymond Brown - X4024 - Cisco 8845 | Raymond Brown | Cisco 8845 | (pending) | pending |
| George Cox - X7005 - Cisco 7821 | George Cox | Cisco 7821 | (pending) | pending |
| Thomas Thompson - X6112 - Cisco 7821 | Thomas Thompson | Cisco 7821 | (pending) | pending |
| Janet Ruiz - X6111 - Cisco 8861 | Janet Ruiz | Cisco 8861 | (pending) | pending |
| Betty Alvarez - X3008 - Cisco 7841 | Betty Alvarez | Cisco 7841 | (pending) | pending |
| Brandon Garcia - X4033 - Cisco 7841 | Brandon Garcia | Cisco 7841 | (pending) | pending |
| Jason Mendoza - X4036 - Cisco 7841 | Jason Mendoza | Cisco 7841 | (pending) | pending |
| Charles Reyes - X3024 - Cisco 7821 | Charles Reyes | Cisco 7821 | (pending) | pending |
| Samantha Howard - X4041 - Cisco 8861 | Samantha Howard | Cisco 8861 | (pending) | pending |
| Kevin Myers - X6118 - Cisco 7841 | Kevin Myers | Cisco 7841 | (pending) | pending |
| Jennifer Kelly - X7013 - Cisco 8861 | Jennifer Kelly | Cisco 8861 | (pending) | pending |
| Jonathan Sanders - X3029 - Cisco 8861 | Jonathan Sanders | Cisco 8861 | (pending) | pending |
| Matthew Castillo - X5013 - Cisco 8845 | Matthew Castillo | Cisco 8845 | (pending) | pending |
| Karen White - X7004 - Cisco 8845 | Karen White | Cisco 8845 | (pending) | pending |
| Gregory Patel - X3003 - Cisco 8845 | Gregory Patel | Cisco 8845 | (pending) | pending |
| Richard Rivera - X3015 - Cisco 8845 | Richard Rivera | Cisco 8845 | (pending) | pending |
| Steven Morris - X7039 - Cisco 7841 | Steven Morris | Cisco 7841 | (pending) | pending |
| Ronald Ortiz - X5006 - Cisco 7841 | Ronald Ortiz | Cisco 7841 | (pending) | pending |
| Mark Evans - X5027 - Cisco 8845 | Mark Evans | Cisco 8845 | (pending) | pending |
| Brian Chavez - X5032 - Cisco 7841 | Brian Chavez | Cisco 7841 | (pending) | pending |
| Nicole King - X3016 - Cisco 8832 | Nicole King | Cisco 8832 | (pending) | pending |
| Dorothy Perez - X7022 - Cisco 7841 | Dorothy Perez | Cisco 7841 | (pending) | pending |
| Nicholas Mendoza - X7027 - Cisco 8832 | Nicholas Mendoza | Cisco 8832 | (pending) | pending |
| Rebecca Ramos - X4005 - Cisco 8845 | Rebecca Ramos | Cisco 8845 | (pending) | pending |
| Nicole Brooks - X3028 - Cisco 7841 | Nicole Brooks | Cisco 7841 | (pending) | pending |
| William Robinson - X3023 - Cisco 8861 | William Robinson | Cisco 8861 | (pending) | pending |
| Ryan Kim - X7023 - Cisco 8845 | Ryan Kim | Cisco 8845 | (pending) | pending |
| Alexander Rodriguez - X3021 - Cisco 7841 | Alexander Rodriguez | Cisco 7841 | (pending) | pending |
| Samuel Sanders - X5000 - Cisco 8861 | Samuel Sanders | Cisco 8861 | (pending) | pending |
| Eric Turner - X7006 - Cisco 7821 | Eric Turner | Cisco 7821 | (pending) | pending |
| Eric Turner - X7035 - Cisco 8845 | Eric Turner | Cisco 8845 | (pending) | pending |
| Jennifer Kelly - X7013 - Cisco 8861 | Jennifer Kelly | Cisco 8861 | (pending) | pending |
| Scott Jackson - X7020 - Cisco 7841 | Scott Jackson | Cisco 7841 | (pending) | pending |
| Patrick Sanders - X6143 - Cisco 8845 | Patrick Sanders | Cisco 8845 | (pending) | pending |
| Debra Mitchell - X4011 - Cisco 8845 | Debra Mitchell | Cisco 8845 | (pending) | pending |
| Rebecca Lewis - X3009 - Cisco 8845 | Rebecca Lewis | Cisco 8845 | (pending) | pending |
| Gregory Castillo - X5009 - Cisco 8832 | Gregory Castillo | Cisco 8832 | (pending) | pending |
| Dorothy Myers - X3041 - Cisco 8861 | Dorothy Myers | Cisco 8861 | (pending) | pending |
| Linda Perez - X7014 - Cisco 7821 | Linda Perez | Cisco 7821 | (pending) | pending |
| Gary Ward - X4007 - Cisco 7841 | Gary Ward | Cisco 7841 | (pending) | pending |
| Karen White - X7004 - Cisco 7841 | Karen White | Cisco 7841 | (pending) | pending |
| Samuel Collins - X3038 - Cisco 8832 | Samuel Collins | Cisco 8832 | (pending) | pending |
| Raymond Brown - X4024 - Cisco 7821 | Raymond Brown | Cisco 7821 | (pending) | pending |
| Jason Morgan - X5010 - Cisco 8845 | Jason Morgan | Cisco 8845 | (pending) | pending |
| Scott Jones - X7030 - Cisco 8861 | Scott Jones | Cisco 8861 | (pending) | pending |
| Nicole Jackson - X4039 - Cisco 7821 | Nicole Jackson | Cisco 7821 | (pending) | pending |
| Jacob Morris - X7019 - Cisco 8845 | Jacob Morris | Cisco 8845 | (pending) | pending |
| Charles Chavez - X7009 - Cisco 7841 | Charles Chavez | Cisco 7841 | (pending) | pending |
| Angela Murphy - X3044 - Cisco 8845 | Angela Murphy | Cisco 8845 | (pending) | pending |
| Raymond Robinson - X3022 - Cisco 8845 | Raymond Robinson | Cisco 8845 | (pending) | pending |
| Patrick Sanders - X6143 - Cisco 7821 | Patrick Sanders | Cisco 7821 | (pending) | pending |
| Stephanie Cruz - X5020 - Cisco 8845 | Stephanie Cruz | Cisco 8845 | (pending) | pending |
| Raymond Ramirez - X4015 - Cisco 8845 | Raymond Ramirez | Cisco 8845 | (pending) | pending |
| Shirley Green - X5033 - Cisco 7841 | Shirley Green | Cisco 7841 | (pending) | pending |
| Kenneth King - X6133 - Cisco 7821 | Kenneth King | Cisco 7821 | (pending) | pending |
| Mark Bennett - X6109 - Cisco 8832 | Mark Bennett | Cisco 8832 | (pending) | pending |
| Kenneth Phillips - X3034 - Cisco 8845 | Kenneth Phillips | Cisco 8845 | (pending) | pending |
| Nicole Smith - X7000 - Cisco 7841 | Nicole Smith | Cisco 7841 | (pending) | pending |
| Kevin Chavez - X5042 - Cisco 7821 | Kevin Chavez | Cisco 7821 | (pending) | pending |
| Daniel Price - X6107 - Cisco 7821 | Daniel Price | Cisco 7821 | (pending) | pending |
| Carolyn Adams - X4042 - Cisco 7821 | Carolyn Adams | Cisco 7821 | (pending) | pending |
| Kathleen Gray - X7007 - Cisco 8845 | Kathleen Gray | Cisco 8845 | (pending) | pending |
| David Ramirez - X3035 - Cisco 7841 | David Ramirez | Cisco 7841 | (pending) | pending |
| Alexander Rodriguez - X3021 - Cisco 7841 | Alexander Rodriguez | Cisco 7841 | (pending) | pending |
| Nancy Gutierrez - X7015 - Cisco 8861 | Nancy Gutierrez | Cisco 8861 | (pending) | pending |
| Richard Rivera - X3015 - Cisco 7821 | Richard Rivera | Cisco 7821 | (pending) | pending |
| Margaret Cruz - X4009 - Cisco 7821 | Margaret Cruz | Cisco 7821 | (pending) | pending |
| Stephanie Cruz - X5020 - Cisco 8845 | Stephanie Cruz | Cisco 8845 | (pending) | pending |
| Kimberly Jones - X4008 - Cisco 7841 | Kimberly Jones | Cisco 7841 | (pending) | pending |
| Laura Kim - X5018 - Cisco 8845 | Laura Kim | Cisco 8845 | (pending) | pending |
| Edward Martin - X5034 - Cisco 8861 | Edward Martin | Cisco 8861 | (pending) | pending |
| Sandra Martinez - X7002 - Cisco 8861 | Sandra Martinez | Cisco 8861 | (pending) | pending |
| Jessica Carter - X3018 - Cisco 8845 | Jessica Carter | Cisco 8845 | (pending) | pending |
| Brian Allen - X6124 - Cisco 8861 | Brian Allen | Cisco 8861 | (pending) | pending |
| Gregory Patel - X3003 - Cisco 7821 | Gregory Patel | Cisco 7821 | (pending) | pending |
| Shirley Anderson - X4029 - Cisco 7841 | Shirley Anderson | Cisco 7841 | (pending) | pending |
| Mark Evans - X5027 - Cisco 7841 | Mark Evans | Cisco 7841 | (pending) | pending |
| Alexander Brown - X6138 - Cisco 7841 | Alexander Brown | Cisco 7841 | (pending) | pending |
| Daniel Stewart - X7029 - Cisco 7841 | Daniel Stewart | Cisco 7841 | (pending) | pending |
| Ryan Cook - X4044 - Cisco 8861 | Ryan Cook | Cisco 8861 | (pending) | pending |
| Scott Ward - X6137 - Cisco 8845 | Scott Ward | Cisco 8845 | (pending) | pending |
| Scott Ortiz - X4043 - Cisco 8845 | Scott Ortiz | Cisco 8845 | (pending) | pending |
| Gregory Castillo - X5009 - Cisco 8861 | Gregory Castillo | Cisco 8861 | (pending) | pending |
| Nicholas Mendoza - X7027 - Cisco 8845 | Nicholas Mendoza | Cisco 8845 | (pending) | pending |
| Carol Scott - X3012 - Cisco 8861 | Carol Scott | Cisco 8861 | (pending) | pending |
| Rebecca Ramos - X4005 - Cisco 8845 | Rebecca Ramos | Cisco 8845 | (pending) | pending |
| Karen Cox - X7028 - Cisco 8832 | Karen Cox | Cisco 8832 | (pending) | pending |
| Nancy Richardson - X7021 - Cisco 7821 | Nancy Richardson | Cisco 7821 | (pending) | pending |
| Christopher Taylor - X4022 - Cisco 8845 | Christopher Taylor | Cisco 8845 | (pending) | pending |
| Karen Cox - X7028 - Cisco 7821 | Karen Cox | Cisco 7821 | (pending) | pending |
| Susan Murphy - X6117 - Cisco 8861 | Susan Murphy | Cisco 8861 | (pending) | pending |
| Benjamin Gray - X5030 - Cisco 8861 | Benjamin Gray | Cisco 8861 | (pending) | pending |
| Rebecca Lewis - X3009 - Cisco 8845 | Rebecca Lewis | Cisco 8845 | (pending) | pending |
| Jonathan Sanders - X3029 - Cisco 7821 | Jonathan Sanders | Cisco 7821 | (pending) | pending |
| Katherine Perez - X6139 - Cisco 7821 | Katherine Perez | Cisco 7821 | (pending) | pending |
| Ryan Cook - X4044 - Cisco 8861 | Ryan Cook | Cisco 8861 | (pending) | pending |
| Deborah Taylor - X7025 - Cisco 7821 | Deborah Taylor | Cisco 7821 | (pending) | pending |
| Carolyn Adams - X4042 - Cisco 7821 | Carolyn Adams | Cisco 7821 | (pending) | pending |
| Margaret Cruz - X4009 - Cisco 8832 | Margaret Cruz | Cisco 8832 | (pending) | pending |
| Carol Scott - X3012 - Cisco 7821 | Carol Scott | Cisco 7821 | (pending) | pending |
| Timothy Scott - X3024 - Cisco 7841 | Timothy Scott | Cisco 7841 | (pending) | pending |
| Dorothy Perez - X7022 - Cisco 8845 | Dorothy Perez | Cisco 8845 | (pending) | pending |
| Samuel Rivera - X4012 - Cisco 7841 | Samuel Rivera | Cisco 7841 | (pending) | pending |
| Stephen Nguyen - X3019 - Cisco 7821 | Stephen Nguyen | Cisco 7821 | (pending) | pending |
| Melissa Rivera - X3026 - Cisco 8832 | Melissa Rivera | Cisco 8832 | (pending) | pending |
| Samuel Rivera - X4012 - Cisco 8845 | Samuel Rivera | Cisco 8845 | (pending) | pending |
| Margaret Ross - X3013 - Cisco 7841 | Margaret Ross | Cisco 7841 | (pending) | pending |
| Jason Robinson - X7037 - Cisco 8861 | Jason Robinson | Cisco 8861 | (pending) | pending |
| Shirley Green - X5033 - Cisco 8845 | Shirley Green | Cisco 8845 | (pending) | pending |
| Thomas Scott - X4033 - Cisco 8845 | Thomas Scott | Cisco 8845 | (pending) | pending |
| Brenda Murphy - X5031 - Cisco 8845 | Brenda Murphy | Cisco 8845 | (pending) | pending |
| Jennifer Jones - X4035 - Cisco 8861 | Jennifer Jones | Cisco 8861 | (pending) | pending |
| Deborah Collins - X4003 - Cisco 7821 | Deborah Collins | Cisco 7821 | (pending) | pending |
| Donald Campbell - X4010 - Cisco 7841 | Donald Campbell | Cisco 7841 | (pending) | pending |
| Sarah Cook - X5022 - Cisco 8861 | Sarah Cook | Cisco 8861 | (pending) | pending |
| Steven Thompson - X4023 - Cisco 8861 | Steven Thompson | Cisco 8861 | (pending) | pending |
| Barbara Morris - X7032 - Cisco 8861 | Barbara Morris | Cisco 8861 | (pending) | pending |
| David Robinson - X7024 - Cisco 8845 | David Robinson | Cisco 8845 | (pending) | pending |
| John Nguyen - X6132 - Cisco 8832 | John Nguyen | Cisco 8832 | (pending) | pending |
| Scott Ward - X6137 - Cisco 7841 | Scott Ward | Cisco 7841 | (pending) | pending |
| Ronald Scott - X4013 - Cisco 8845 | Ronald Scott | Cisco 8845 | (pending) | pending |
| Mark Bennett - X6109 - Cisco 7841 | Mark Bennett | Cisco 7841 | (pending) | pending |
| Mark Moore - X3002 - Cisco 7841 | Mark Moore | Cisco 7841 | (pending) | pending |
| Gregory Patel - X3003 - Cisco 8861 | Gregory Patel | Cisco 8861 | (pending) | pending |
| Brian Chavez - X5032 - Cisco 7841 | Brian Chavez | Cisco 7841 | (pending) | pending |
| Charles Moore - X7012 - Cisco 7841 | Charles Moore | Cisco 7841 | (pending) | pending |
| Samantha Howard - X4041 - Cisco 8832 | Samantha Howard | Cisco 8832 | (pending) | pending |
| Robert Young - X7010 - Cisco 8845 | Robert Young | Cisco 8845 | (pending) | pending |
| Karen White - X7004 - Cisco 7841 | Karen White | Cisco 7841 | (pending) | pending |
| Jacob Morris - X7019 - Cisco 8845 | Jacob Morris | Cisco 8845 | (pending) | pending |
| Emma Patel - X5029 - Cisco 8861 | Emma Patel | Cisco 8861 | (pending) | pending |
| Charles Sanders - X6105 - Cisco 8845 | Charles Sanders | Cisco 8845 | (pending) | pending |
| Laura Johnson - X6122 - Cisco 8845 | Laura Johnson | Cisco 8845 | (pending) | pending |
| Melissa Carter - X5001 - Cisco 7841 | Melissa Carter | Cisco 7841 | (pending) | pending |
| Samantha Anderson - X3000 - Cisco 8861 | Samantha Anderson | Cisco 8861 | (pending) | pending |
| Pamela Gutierrez - X7043 - Cisco 8832 | Pamela Gutierrez | Cisco 8832 | (pending) | pending |
| Deborah Cruz - X6126 - Cisco 8845 | Deborah Cruz | Cisco 8845 | (pending) | pending |
| Kenneth Kelly - X5024 - Cisco 7841 | Kenneth Kelly | Cisco 7841 | (pending) | pending |
| Pamela Wood - X6118 - Cisco 8845 | Pamela Wood | Cisco 8845 | (pending) | pending |
| Kenneth King - X6133 - Cisco 8861 | Kenneth King | Cisco 8861 | (pending) | pending |
| Timothy Carter - X5002 - Cisco 8845 | Timothy Carter | Cisco 8845 | (pending) | pending |
| Jonathan Sanders - X3029 - Cisco 8845 | Jonathan Sanders | Cisco 8845 | (pending) | pending |
| Thomas Patel - X4028 - Cisco 8845 | Thomas Patel | Cisco 8845 | (pending) | pending |
| Kathleen Gray - X7007 - Cisco 8861 | Kathleen Gray | Cisco 8861 | (pending) | pending |
| Kimberly Jones - X4008 - Cisco 8832 | Kimberly Jones | Cisco 8832 | (pending) | pending |
| Brandon Foster - X5015 - Cisco 7821 | Brandon Foster | Cisco 7821 | (pending) | pending |
| Kenneth Kelly - X5024 - Cisco 8845 | Kenneth Kelly | Cisco 8845 | (pending) | pending |
| Robert Hill - X5008 - Cisco 8845 | Robert Hill | Cisco 8845 | (pending) | pending |
| John Nguyen - X6132 - Cisco 8861 | John Nguyen | Cisco 8861 | (pending) | pending |
| Barbara Ramos - X3004 - Cisco 7841 | Barbara Ramos | Cisco 7841 | (pending) | pending |
| Pamela Wood - X6130 - Cisco 7841 | Pamela Wood | Cisco 7841 | (pending) | pending |
| Timothy White - X5040 - Cisco 7841 | Timothy White | Cisco 7841 | (pending) | pending |
| Samantha Anderson - X3027 - Cisco 7821 | Samantha Anderson | Cisco 7821 | (pending) | pending |
| Nicole King - X3016 - Cisco 8845 | Nicole King | Cisco 8845 | (pending) | pending |
| Melissa Price - X6102 - Cisco 8845 | Melissa Price | Cisco 8845 | (pending) | pending |
| Rebecca Wood - X4006 - Cisco 7841 | Rebecca Wood | Cisco 7841 | (pending) | pending |
| Alexander Bennett - X6121 - Cisco 7841 | Alexander Bennett | Cisco 7841 | (pending) | pending |
| Jessica Thompson - X5005 - Cisco 8845 | Jessica Thompson | Cisco 8845 | (pending) | pending |
| Matthew Evans - X6142 - Cisco 7841 | Matthew Evans | Cisco 7841 | (pending) | pending |
| Steven Thompson - X4023 - Cisco 8861 | Steven Thompson | Cisco 8861 | (pending) | pending |
| Ryan Kim - X7023 - Cisco 8861 | Ryan Kim | Cisco 8861 | (pending) | pending |
| Angela Ramos - X4031 - Cisco 8861 | Angela Ramos | Cisco 8861 | (pending) | pending |
| Jessica Carter - X3018 - Cisco 7841 | Jessica Carter | Cisco 7841 | (pending) | pending |
| Steven Morris - X7039 - Cisco 7841 | Steven Morris | Cisco 7841 | (pending) | pending |
| Joshua Price - X5037 - Cisco 8845 | Joshua Price | Cisco 8845 | (pending) | pending |
| Laura Johnson - X6122 - Cisco 8845 | Laura Johnson | Cisco 8845 | (pending) | pending |
| Rachel Kelly - X6113 - Cisco 8845 | Rachel Kelly | Cisco 8845 | (pending) | pending |
| Samantha Campbell - X3025 - Cisco 7841 | Samantha Campbell | Cisco 7841 | (pending) | pending |
| Raymond Torres - X7017 - Cisco 8861 | Raymond Torres | Cisco 8861 | (pending) | pending |
| Thomas Thompson - X6112 - Cisco 7841 | Thomas Thompson | Cisco 7841 | (pending) | pending |
| Emma Patel - X5029 - Cisco 8845 | Emma Patel | Cisco 8845 | (pending) | pending |
| Laura Cook - X4032 - Cisco 8832 | Laura Cook | Cisco 8832 | (pending) | pending |
| Joshua Adams - X6104 - Cisco 8861 | Joshua Adams | Cisco 8861 | (pending) | pending |
| Gary Ward - X4007 - Cisco 8845 | Gary Ward | Cisco 8845 | (pending) | pending |
| Deborah Taylor - X7025 - Cisco 7841 | Deborah Taylor | Cisco 7841 | (pending) | pending |
| Brenda Murphy - X5031 - Cisco 7821 | Brenda Murphy | Cisco 7821 | (pending) | pending |
| Timothy Carter - X5002 - Cisco 8845 | Timothy Carter | Cisco 8845 | (pending) | pending |
| Anna Ramirez - X5021 - Cisco 8845 | Anna Ramirez | Cisco 8845 | (pending) | pending |
| Alexander Brown - X6138 - Cisco 7841 | Alexander Brown | Cisco 7841 | (pending) | pending |
| Brian Martin - X5012 - Cisco 8845 | Brian Martin | Cisco 8845 | (pending) | pending |
| Nicole Smith - X7000 - Cisco 8861 | Nicole Smith | Cisco 8861 | (pending) | pending |
| Matthew Castillo - X5013 - Cisco 8861 | Matthew Castillo | Cisco 8861 | (pending) | pending |
| Lisa Brooks - X6107 - Cisco 8845 | Lisa Brooks | Cisco 8845 | (pending) | pending |
| Richard Rivera - X3034 - Cisco 7821 | Richard Rivera | Cisco 7821 | (pending) | pending |
| Jennifer Hughes - X7036 - Cisco 7841 | Jennifer Hughes | Cisco 7841 | (pending) | pending |
| Dorothy Moore - X3039 - Cisco 7841 | Dorothy Moore | Cisco 7841 | (pending) | pending |
| Ashley Patel - X5019 - Cisco 7841 | Ashley Patel | Cisco 7841 | (pending) | pending |
| Scott Jackson - X7020 - Cisco 7821 | Scott Jackson | Cisco 7821 | (pending) | pending |
| Lisa Evans - X6127 - Cisco 8845 | Lisa Evans | Cisco 8845 | (pending) | pending |
| Christine Wright - X3027 - Cisco 7841 | Christine Wright | Cisco 7841 | (pending) | pending |
| Jessica Thompson - X5005 - Cisco 7821 | Jessica Thompson | Cisco 7821 | (pending) | pending |
| Stephanie Cruz - X5020 - Cisco 7821 | Stephanie Cruz | Cisco 7821 | (pending) | pending |
| Linda Morris - X4035 - Cisco 7841 | Linda Morris | Cisco 7841 | (pending) | pending |
| Eric Turner - X7035 - Cisco 8845 | Eric Turner | Cisco 8845 | (pending) | pending |
| John James - X5014 - Cisco 7821 | John James | Cisco 7821 | (pending) | pending |
| Pamela Gutierrez - X7043 - Cisco 7841 | Pamela Gutierrez | Cisco 7841 | (pending) | pending |
| Donald Clark - X5016 - Cisco 8861 | Donald Clark | Cisco 8861 | (pending) | pending |
| Kenneth Kelly - X5024 - Cisco 7821 | Kenneth Kelly | Cisco 7821 | (pending) | pending |
| Mary Rivera - X4025 - Cisco 7841 | Mary Rivera | Cisco 7841 | (pending) | pending |
| Mark Mendoza - X3032 - Cisco 7841 | Mark Mendoza | Cisco 7841 | (pending) | pending |
| Joshua Collins - X4034 - Cisco 7841 | Joshua Collins | Cisco 7841 | (pending) | pending |
| Jason Mendoza - X4036 - Cisco 8861 | Jason Mendoza | Cisco 8861 | (pending) | pending |
| Timothy Carter - X5002 - Cisco 8845 | Timothy Carter | Cisco 8845 | (pending) | pending |
| Dorothy Moore - X3039 - Cisco 8832 | Dorothy Moore | Cisco 8832 | (pending) | pending |
| Melissa Rivera - X3026 - Cisco 7821 | Melissa Rivera | Cisco 7821 | (pending) | pending |
| Charles Chavez - X7009 - Cisco 8861 | Charles Chavez | Cisco 8861 | (pending) | pending |
| Melissa Price - X6102 - Cisco 8845 | Melissa Price | Cisco 8845 | (pending) | pending |
| Linda Robinson - X3033 - Cisco 8845 | Linda Robinson | Cisco 8845 | (pending) | pending |
| Jack Scott - X3001 - Cisco 8845 | Jack Scott | Cisco 8845 | (pending) | pending |
| Dorothy James - X6144 - Cisco 8832 | Dorothy James | Cisco 8832 | (pending) | pending |
| Mark Bennett - X6109 - Cisco 8832 | Mark Bennett | Cisco 8832 | (pending) | pending |
| Robert Miller - X4016 - Cisco 7821 | Robert Miller | Cisco 7821 | (pending) | pending |
| William Robinson - X3023 - Cisco 7821 | William Robinson | Cisco 7821 | (pending) | pending |
| Robert Young - X7010 - Cisco 8845 | Robert Young | Cisco 8845 | (pending) | pending |
| Matthew Castillo - X5013 - Cisco 7841 | Matthew Castillo | Cisco 7841 | (pending) | pending |
| Elizabeth Baker - X6134 - Cisco 7841 | Elizabeth Baker | Cisco 7841 | (pending) | pending |
| Nicole Green - X6107 - Cisco 8845 | Nicole Green | Cisco 8845 | (pending) | pending |
| Matthew Smith - X7042 - Cisco 8845 | Matthew Smith | Cisco 8845 | (pending) | pending |
| Emma Gonzalez - X6103 - Cisco 8845 | Emma Gonzalez | Cisco 8845 | (pending) | pending |
| Nicole Cooper - X7033 - Cisco 8845 | Nicole Cooper | Cisco 8845 | (pending) | pending |
| Samuel Rivera - X4012 - Cisco 8861 | Samuel Rivera | Cisco 8861 | (pending) | pending |
| Larry Jones - X6114 - Cisco 8832 | Larry Jones | Cisco 8832 | (pending) | pending |
| Shirley Green - X5033 - Cisco 8845 | Shirley Green | Cisco 8845 | (pending) | pending |
| Daniel Stewart - X7029 - Cisco 8845 | Daniel Stewart | Cisco 8845 | (pending) | pending |
| Catherine Bailey - X3040 - Cisco 7841 | Catherine Bailey | Cisco 7841 | (pending) | pending |
| Katherine Perez - X6139 - Cisco 8845 | Katherine Perez | Cisco 8845 | (pending) | pending |
| Thomas Scott - X4040 - Cisco 8845 | Thomas Scott | Cisco 8845 | (pending) | pending |
| Jessica Thompson - X5005 - Cisco 7821 | Jessica Thompson | Cisco 7821 | (pending) | pending |
| John Brown - X3005 - Cisco 8861 | John Brown | Cisco 8861 | (pending) | pending |
| Karen Cox - X7028 - Cisco 8861 | Karen Cox | Cisco 8861 | (pending) | pending |
| Sandra Young - X5011 - Cisco 7841 | Sandra Young | Cisco 7841 | (pending) | pending |
| Sarah Cook - X5022 - Cisco 8845 | Sarah Cook | Cisco 8845 | (pending) | pending |
| Timothy Gonzalez - X6129 - Cisco 8861 | Timothy Gonzalez | Cisco 8861 | (pending) | pending |
| Samuel Sanders - X5037 - Cisco 8845 | Samuel Sanders | Cisco 8845 | (pending) | pending |
| Larry Jones - X6114 - Cisco 7841 | Larry Jones | Cisco 7841 | (pending) | pending |
| Sandra Sanders - X5023 - Cisco 8845 | Sandra Sanders | Cisco 8845 | (pending) | pending |
| Ronald Ortiz - X5006 - Cisco 8845 | Ronald Ortiz | Cisco 8845 | (pending) | pending |
| Catherine Bailey - X3012 - Cisco 7821 | Catherine Bailey | Cisco 7821 | (pending) | pending |
| Christopher Jimenez - X6100 - Cisco 7841 | Christopher Jimenez | Cisco 7841 | (pending) | pending |
| Thomas Kelly - X7011 - Cisco 8861 | Thomas Kelly | Cisco 8861 | (pending) | pending |
| Timothy Hall - X6128 - Cisco 8861 | Timothy Hall | Cisco 8861 | (pending) | pending |
| Jessica Collins - X4014 - Cisco 7821 | Jessica Collins | Cisco 7821 | (pending) | pending |
| George Lewis - X3043 - Cisco 7821 | George Lewis | Cisco 7821 | (pending) | pending |
| Emma Gonzalez - X6103 - Cisco 7841 | Emma Gonzalez | Cisco 7841 | (pending) | pending |
| Jacob Walker - X5036 - Cisco 8845 | Jacob Walker | Cisco 8845 | (pending) | pending |
| Ashley Taylor - X4017 - Cisco 8845 | Ashley Taylor | Cisco 8845 | (pending) | pending |
| Linda Robinson - X3033 - Cisco 7841 | Linda Robinson | Cisco 7841 | (pending) | pending |
| Anthony Ramos - X4019 - Cisco 7841 | Anthony Ramos | Cisco 7841 | (pending) | pending |
| Eric Smith - X7044 - Cisco 8845 | Eric Smith | Cisco 8845 | (pending) | pending |
| Raymond Torres - X7017 - Cisco 8861 | Raymond Torres | Cisco 8861 | (pending) | pending |
| Gregory Wood - X7034 - Cisco 7821 | Gregory Wood | Cisco 7821 | (pending) | pending |
| Christopher Taylor - X4022 - Cisco 7841 | Christopher Taylor | Cisco 7841 | (pending) | pending |
| Samantha Morales - X6106 - Cisco 8861 | Samantha Morales | Cisco 8861 | (pending) | pending |
| Timothy Carter - X5002 - Cisco 8861 | Timothy Carter | Cisco 8861 | (pending) | pending |
| Gary Alvarez - X4037 - Cisco 8861 | Gary Alvarez | Cisco 8861 | (pending) | pending |
| Jason Mendoza - X4036 - Cisco 8861 | Jason Mendoza | Cisco 8861 | (pending) | pending |
| Timothy White - X5035 - Cisco 8845 | Timothy White | Cisco 8845 | (pending) | pending |
| Susan Lopez - X3014 - Cisco 7841 | Susan Lopez | Cisco 7841 | (pending) | pending |
| George Kelly - X3020 - Cisco 7821 | George Kelly | Cisco 7821 | (pending) | pending |
| Scott Reed - X7016 - Cisco 8845 | Scott Reed | Cisco 8845 | (pending) | pending |
| Samuel Sanders - X5000 - Cisco 7821 | Samuel Sanders | Cisco 7821 | (pending) | pending |
| Melissa Price - X6102 - Cisco 8861 | Melissa Price | Cisco 8861 | (pending) | pending |
| Amy Anderson - X4001 - Cisco 8861 | Amy Anderson | Cisco 8861 | (pending) | pending |
| Kevin Chavez - X5042 - Cisco 8845 | Kevin Chavez | Cisco 8845 | (pending) | pending |
| Daniel Carter - X6110 - Cisco 8845 | Daniel Carter | Cisco 8845 | (pending) | pending |
| Rebecca Nelson - X7006 - Cisco 8861 | Rebecca Nelson | Cisco 8861 | (pending) | pending |
| Ryan Cook - X4044 - Cisco 8845 | Ryan Cook | Cisco 8845 | (pending) | pending |
| Debra Mitchell - X4011 - Cisco 7841 | Debra Mitchell | Cisco 7841 | (pending) | pending |
| Robert Sanchez - X7026 - Cisco 8832 | Robert Sanchez | Cisco 8832 | (pending) | pending |
| Charles Sanders - X6105 - Cisco 7821 | Charles Sanders | Cisco 7821 | (pending) | pending |
| Dorothy James - X6144 - Cisco 7821 | Dorothy James | Cisco 7821 | (pending) | pending |
| Christine Wright - X3027 - Cisco 8845 | Christine Wright | Cisco 8845 | (pending) | pending |

## 6. Estimated Impact

| What Changes | Details |
|-------------|---------|
| Users added | 300 new Webex Calling users |
| Workspaces added | 4 new workspaces |
| Devices provisioned | 1100 devices |
| Licenses consumed | 304 Webex Calling Professional (300 user + 4 workspace) |
| Locations created | 6 new locations |
| Total operations | 1875 |
| Estimated API calls | 2858 calls (~29 min at 100 req/min) |

## 7. Rollback Strategy

Execution is tracked per-operation in the migration database. Rollback deletes created resources in reverse dependency order. Use `wxcli cucm rollback` to initiate.

## 8. Approval

Review the plan above. The migration skill will not execute until you confirm.

- [ ] **I approve this deployment plan.** Proceed with execution.
- [ ] **I need changes.** [Describe what to modify]
- [ ] **Cancel.** Do not execute.
