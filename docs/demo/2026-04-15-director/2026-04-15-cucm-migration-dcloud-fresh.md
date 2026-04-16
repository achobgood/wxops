# Deployment Plan: CUCM Migration — dcloud-fresh

Created: 2026-04-15
Agent: wxc-calling-builder

---

## 1. Objective

Migrate 300 users, 1100 devices, 4 workspaces, 71 call features from CUCM to Webex Calling (project: dcloud-fresh).
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
| D0363 | WORKSPACE_TYPE_UNCERTAIN | Common-area device 'dCloud_CER_P2' has ambiguous workspace classification — device pool '' does not clearly indicate room type | Accept fidelity loss |
| D0366 | WORKSPACE_TYPE_UNCERTAIN | Common-area device 'dCloud_CER_P3' has ambiguous workspace classification — device pool '' does not clearly indicate room type | Accept fidelity loss |
| D0368 | WORKSPACE_TYPE_UNCERTAIN | Common-area device 'dCloud_CER_P1' has ambiguous workspace classification — device pool '' does not clearly indicate room type | Accept fidelity loss |
| D1403 | FORWARDING_LOSSY | User 'mkumar' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1404 | FORWARDING_LOSSY | User 'amckenzie' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1405 | FORWARDING_LOSSY | User 'cholland' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1406 | FORWARDING_LOSSY | User 'smiller' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1407 | FORWARDING_LOSSY | User 'jli' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1408 | FORWARDING_LOSSY | User 'mcheng' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1409 | FORWARDING_LOSSY | User 'tbard' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1410 | FORWARDING_LOSSY | User 'aperez' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1411 | FORWARDING_LOSSY | User 'nfox' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1412 | FORWARDING_LOSSY | User 'wwhitman' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1413 | FORWARDING_LOSSY | User 'smacks' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1414 | FORWARDING_LOSSY | User 'chegarty' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1415 | FORWARDING_LOSSY | User 'kmelby' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1416 | FORWARDING_LOSSY | User 'bburke' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1417 | FORWARDING_LOSSY | User 'smckenna' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1418 | FORWARDING_LOSSY | User 'jxu' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1419 | FORWARDING_LOSSY | User 'dcebu' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1420 | FORWARDING_LOSSY | User 'fudinese' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1421 | FORWARDING_LOSSY | User 'blapointe' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1422 | FORWARDING_LOSSY | User 'mbrown' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1423 | FORWARDING_LOSSY | User 'rkhan' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1424 | FORWARDING_LOSSY | User 'jionello' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1425 | FORWARDING_LOSSY | User 'vkara' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1426 | FORWARDING_LOSSY | User 'adelamico' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1427 | FORWARDING_LOSSY | User 'mrossi' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1428 | FORWARDING_LOSSY | User 'avargas' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1429 | FORWARDING_LOSSY | User 'bstarr' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1430 | FORWARDING_LOSSY | User 'gstanislaus' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1431 | FORWARDING_LOSSY | User 'kfinney' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1432 | FORWARDING_LOSSY | User 'bgerman' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1433 | FORWARDING_LOSSY | User 'kadams' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1434 | FORWARDING_LOSSY | User 'rsmith' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1435 | FORWARDING_LOSSY | User 'msimek' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1436 | FORWARDING_LOSSY | User 'ribsen' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1437 | FORWARDING_LOSSY | User 'eyamadaya' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1438 | FORWARDING_LOSSY | User 'acassidy' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1439 | FORWARDING_LOSSY | User 'jweston' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1440 | FORWARDING_LOSSY | User 'pdudley' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1441 | FORWARDING_LOSSY | User 'cmccullen' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1442 | FORWARDING_LOSSY | User 'scentineo' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1443 | FORWARDING_LOSSY | User 'csinu' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1444 | FORWARDING_LOSSY | User 'cshor' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1445 | FORWARDING_LOSSY | User 'norr' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1446 | FORWARDING_LOSSY | User 'schristopolous' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1447 | FORWARDING_LOSSY | User 'gedwards' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1448 | FORWARDING_LOSSY | User 'sjones' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1449 | FORWARDING_LOSSY | User 'ffoster' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1450 | FORWARDING_LOSSY | User 'pseong' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1451 | FORWARDING_LOSSY | User 'akarlsson' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1452 | FORWARDING_LOSSY | User 'acondor' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1453 | FORWARDING_LOSSY | User 'amaguire' has 7 CUCM-only forwarding variant(s): callForwardBusyInt, callForwardNoAnswerInt, callForwardNoCoverage, callForwardNoCoverageInt, callForwardOnFailure, callForwardNotRegistered, callForwardNotRegisteredInt | Accept fidelity loss |
| D1454 | BUTTON_UNMAPPABLE | Template 'Cisco DX80 SIP' has 1 button(s) with no Webex equivalent: Redial (2 phones affected) | Accept loss |
| D1455 | BUTTON_UNMAPPABLE | Template 'Cisco DX70 SIP' has 1 button(s) with no Webex equivalent: Redial (2 phones affected) | Accept loss |
| D1456 | BUTTON_UNMAPPABLE | Template 'Cisco dCloud 8851 SIP' has 1 button(s) with no Webex equivalent: Hunt Group Logout (2 phones affected) | Accept loss |
| D1457 | BUTTON_UNMAPPABLE | Template 'Cisco dCloud DX650 SIP' has 1 button(s) with no Webex equivalent: Hunt Group Logout (2 phones affected) | Accept loss |
| D1458 | BUTTON_UNMAPPABLE | Template 'Cisco dCloud 8845 SIP' has 1 button(s) with no Webex equivalent: Hunt Group Logout (2 phones affected) | Accept loss |
| D1459 | BUTTON_UNMAPPABLE | Template 'Cisco dCloud 8865 SIP' has 1 button(s) with no Webex equivalent: Hunt Group Logout (2 phones affected) | Accept loss |
| D1478 | MISSING_DATA | device 'device:G29FD01CF100040' missing required fields: mac | Skip this object |
| D1506 | MISSING_DATA | device 'device:P29FD01CF100110' missing required fields: mac | Skip this object |
| D1469 | MISSING_DATA | device 'device:G29FD01CF100093' missing required fields: mac | Skip this object |
| D1471 | MISSING_DATA | device 'device:G29FD01CF100033' missing required fields: mac | Skip this object |
| D1488 | MISSING_DATA | device 'device:S29FD01CF100102' missing required fields: mac | Skip this object |
| D1504 | MISSING_DATA | device 'device:P29FD01CF100108' missing required fields: mac | Skip this object |
| D1486 | MISSING_DATA | device 'device:S29FD01CF100100' missing required fields: mac | Skip this object |
| D1500 | MISSING_DATA | device 'device:S29FD01CF100074' missing required fields: mac | Skip this object |
| D1464 | MISSING_DATA | device 'device:G29FD01CF100088' missing required fields: mac | Skip this object |
| D1496 | MISSING_DATA | device 'device:S29FD01CF100070' missing required fields: mac | Skip this object |
| D1463 | MISSING_DATA | device 'device:G29FD01CF100087' missing required fields: mac | Skip this object |
| D1466 | MISSING_DATA | device 'device:G29FD01CF100090' missing required fields: mac | Skip this object |
| D1465 | MISSING_DATA | device 'device:G29FD01CF100089' missing required fields: mac | Skip this object |
| D1502 | MISSING_DATA | device 'device:P29FD01CF100106' missing required fields: mac | Skip this object |
| D1480 | MISSING_DATA | device 'device:G29FD01CF100042' missing required fields: mac | Skip this object |
| D1510 | MISSING_DATA | device 'device:P29FD01CF100114' missing required fields: mac | Skip this object |
| D1520 | MISSING_DATA | device 'device:P29FD01CF100084' missing required fields: mac | Skip this object |
| D1508 | MISSING_DATA | device 'device:P29FD01CF100112' missing required fields: mac | Skip this object |
| D1473 | MISSING_DATA | device 'device:G29FD01CF100035' missing required fields: mac | Skip this object |
| D1483 | MISSING_DATA | device 'device:S29FD01CF100097' missing required fields: mac | Skip this object |
| D1491 | MISSING_DATA | device 'device:S29FD01CF100065' missing required fields: mac | Skip this object |
| D1513 | MISSING_DATA | device 'device:P29FD01CF100077' missing required fields: mac | Skip this object |
| D1470 | MISSING_DATA | device 'device:G29FD01CF100094' missing required fields: mac | Skip this object |
| D1467 | MISSING_DATA | device 'device:G29FD01CF100091' missing required fields: mac | Skip this object |
| D1481 | MISSING_DATA | device 'device:S29FD01CF100095' missing required fields: mac | Skip this object |
| D1484 | MISSING_DATA | device 'device:S29FD01CF100098' missing required fields: mac | Skip this object |
| D1497 | MISSING_DATA | device 'device:S29FD01CF100071' missing required fields: mac | Skip this object |
| D1509 | MISSING_DATA | device 'device:P29FD01CF100113' missing required fields: mac | Skip this object |
| D1487 | MISSING_DATA | device 'device:S29FD01CF100101' missing required fields: mac | Skip this object |
| D1490 | MISSING_DATA | device 'device:S29FD01CF100104' missing required fields: mac | Skip this object |
| D1493 | MISSING_DATA | device 'device:S29FD01CF100067' missing required fields: mac | Skip this object |
| D1515 | MISSING_DATA | device 'device:P29FD01CF100079' missing required fields: mac | Skip this object |
| D1489 | MISSING_DATA | device 'device:S29FD01CF100103' missing required fields: mac | Skip this object |
| D1485 | MISSING_DATA | device 'device:S29FD01CF100099' missing required fields: mac | Skip this object |
| D1503 | MISSING_DATA | device 'device:P29FD01CF100107' missing required fields: mac | Skip this object |
| D1477 | MISSING_DATA | device 'device:G29FD01CF100039' missing required fields: mac | Skip this object |
| D1499 | MISSING_DATA | device 'device:S29FD01CF100073' missing required fields: mac | Skip this object |
| D1462 | MISSING_DATA | device 'device:G29FD01CF100086' missing required fields: mac | Skip this object |
| D1460 | WORKSPACE_LICENSE_TIER | Workspace 'Hotel Room 1100' set to Workspace but has Professional Workspace features: hot-desking enabled | Professional Workspace |
| D1516 | MISSING_DATA | device 'device:P29FD01CF100080' missing required fields: mac | Skip this object |
| D1514 | MISSING_DATA | device 'device:P29FD01CF100078' missing required fields: mac | Skip this object |
| D1475 | MISSING_DATA | device 'device:G29FD01CF100037' missing required fields: mac | Skip this object |
| D1472 | MISSING_DATA | device 'device:G29FD01CF100034' missing required fields: mac | Skip this object |
| D1461 | MISSING_DATA | device 'device:G29FD01CF100085' missing required fields: mac | Skip this object |
| D1501 | MISSING_DATA | device 'device:P29FD01CF100105' missing required fields: mac | Skip this object |
| D1495 | MISSING_DATA | device 'device:S29FD01CF100069' missing required fields: mac | Skip this object |
| D1512 | MISSING_DATA | device 'device:P29FD01CF100076' missing required fields: mac | Skip this object |
| D1492 | MISSING_DATA | device 'device:S29FD01CF100066' missing required fields: mac | Skip this object |
| D1468 | MISSING_DATA | device 'device:G29FD01CF100092' missing required fields: mac | Skip this object |
| D1494 | MISSING_DATA | device 'device:S29FD01CF100068' missing required fields: mac | Skip this object |
| D1507 | MISSING_DATA | device 'device:P29FD01CF100111' missing required fields: mac | Skip this object |
| D1517 | MISSING_DATA | device 'device:P29FD01CF100081' missing required fields: mac | Skip this object |
| D1518 | MISSING_DATA | device 'device:P29FD01CF100082' missing required fields: mac | Skip this object |
| D1498 | MISSING_DATA | device 'device:S29FD01CF100072' missing required fields: mac | Skip this object |
| D1482 | MISSING_DATA | device 'device:S29FD01CF100096' missing required fields: mac | Skip this object |
| D1474 | MISSING_DATA | device 'device:G29FD01CF100036' missing required fields: mac | Skip this object |
| D1476 | MISSING_DATA | device 'device:G29FD01CF100038' missing required fields: mac | Skip this object |
| D1479 | MISSING_DATA | device 'device:G29FD01CF100041' missing required fields: mac | Skip this object |
| D1511 | MISSING_DATA | device 'device:P29FD01CF100075' missing required fields: mac | Skip this object |
| D1505 | MISSING_DATA | device 'device:P29FD01CF100109' missing required fields: mac | Skip this object |
| D1519 | MISSING_DATA | device 'device:P29FD01CF100083' missing required fields: mac | Skip this object |
| D1532 | ARCHITECTURE_ADVISORY | 55 remote destinations for 0 users — Webex SNR is simpler, manual setup required | Apply recommendation |
| D1526 | ARCHITECTURE_ADVISORY | CPN transformations on 11 objects need flat Webex caller ID mapping | Apply recommendation |
| D1527 | ARCHITECTURE_ADVISORY | PSTN recommendation: Local Gateway | Apply recommendation |
| D1533 | ARCHITECTURE_ADVISORY | 10 caller ID transformation patterns require manual review | Apply recommendation |
| D1534 | ARCHITECTURE_ADVISORY | 56 Extension Mobility profiles — map to Webex hot desking | Apply recommendation |
| D1522 | ARCHITECTURE_ADVISORY | 405 unknown phones need bulk replacement | Apply recommendation |
| D1528 | ARCHITECTURE_ADVISORY | Dial plan style: hybrid (25% E.164) | Apply recommendation |
| D1529 | ARCHITECTURE_ADVISORY | 1 device pools reference MRGLs — cloud handles media resources | Apply recommendation |
| D1521 | ARCHITECTURE_ADVISORY | 2 translation patterns duplicate Webex native digit normalization | Apply recommendation |
| D1531 | ARCHITECTURE_ADVISORY | 14 users have call recording enabled — enable Webex recording per-user during migration | Apply recommendation |
| D1523 | ARCHITECTURE_ADVISORY | 4 trunks point to 198.18.135.54 — consolidate to one | Apply recommendation |
| D1525 | ARCHITECTURE_ADVISORY | 7 voicemail pilots can be eliminated — Webex uses per-user voicemail | Apply recommendation |
| D1530 | ARCHITECTURE_ADVISORY | E911 configuration detected — requires separate workstream | Apply recommendation |
| D1524 | ARCHITECTURE_ADVISORY | 2 trunks point to 198.18.133.150 — consolidate to one | Apply recommendation |
| D1548 | DUPLICATE_USER | Calling user gedwards@cb231.dc-01.com already exists in Webex | Skip this user |
| D1555 | DUPLICATE_USER | Calling user cshor@cb231.dc-01.com already exists in Webex | Skip this user |
| D1573 | DUPLICATE_USER | Calling user fudinese@cb231.dc-01.com already exists in Webex | Skip this user |
| D1549 | DUPLICATE_USER | Calling user jweston@cb231.dc-01.com already exists in Webex | Skip this user |
| D1571 | DUPLICATE_USER | Calling user kfinney@cb231.dc-01.com already exists in Webex | Skip this user |
| D1574 | DUPLICATE_USER | Calling user pseong@cb231.dc-01.com already exists in Webex | Skip this user |
| D1568 | DUPLICATE_USER | Calling user akarlsson@cb231.dc-01.com already exists in Webex | Skip this user |
| D1564 | DUPLICATE_USER | Calling user jionello@cb231.dc-01.com already exists in Webex | Skip this user |
| D1559 | DUPLICATE_USER | Calling user jxu@cb231.dc-01.com already exists in Webex | Skip this user |
| D1540 | DUPLICATE_USER | Calling user jli@cb231.dc-01.com already exists in Webex | Skip this user |
| D1575 | DUPLICATE_USER | Calling user norr@cb231.dc-01.com already exists in Webex | Skip this user |
| D1562 | DUPLICATE_USER | Calling user schristopolous@cb231.dc-01.com already exists in Webex | Skip this user |
| D1539 | DUPLICATE_USER | Calling user mkumar@cb231.dc-01.com already exists in Webex | Skip this user |
| D1570 | DUPLICATE_USER | Calling user eyamadaya@cb231.dc-01.com already exists in Webex | Skip this user |
| D1538 | DUPLICATE_USER | Calling user nfox@cb231.dc-01.com already exists in Webex | Skip this user |
| D1556 | DUPLICATE_USER | Calling user pdudley@cb231.dc-01.com already exists in Webex | Skip this user |
| D1567 | DUPLICATE_USER | Calling user ffoster@cb231.dc-01.com already exists in Webex | Skip this user |
| D1557 | DUPLICATE_USER | Calling user rsmith@cb231.dc-01.com already exists in Webex | Skip this user |
| D1546 | DUPLICATE_USER | Calling user bburke@cb231.dc-01.com already exists in Webex | Skip this user |
| D1577 | DUPLICATE_USER | Calling user bstarr@cb231.dc-01.com already exists in Webex | Skip this user |
| D1544 | DUPLICATE_USER | Calling user bgerman@cb231.dc-01.com already exists in Webex | Skip this user |
| D1558 | DUPLICATE_USER | Calling user avargas@cb231.dc-01.com already exists in Webex | Skip this user |
| D1560 | DUPLICATE_USER | Calling user rkhan@cb231.dc-01.com already exists in Webex | Skip this user |
| D1547 | DUPLICATE_USER | Calling user csinu@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1535 | DUPLICATE_USER | Calling user amckenzie@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1572 | DUPLICATE_USER | Calling user vkara@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1578 | DUPLICATE_USER | Calling user msimek@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1561 | DUPLICATE_USER | Calling user cmccullen@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1542 | DUPLICATE_USER | Calling user acassidy@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1552 | DUPLICATE_USER | Calling user mrossi@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1541 | DUPLICATE_USER | Calling user mcheng@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1576 | DUPLICATE_USER | Calling user acondor@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1536 | DUPLICATE_USER | Calling user tadams@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1551 | DUPLICATE_USER | Calling user mbrown@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1545 | DUPLICATE_USER | Calling user blapointe@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1554 | DUPLICATE_USER | Calling user sjones@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1566 | DUPLICATE_USER | Calling user dcebu@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1537 | DUPLICATE_USER | Calling user wwhitman@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1565 | DUPLICATE_USER | Calling user gstanislaus@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1543 | DUPLICATE_USER | Calling user adelamico@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1550 | DUPLICATE_USER | Calling user kadams@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1563 | DUPLICATE_USER | Calling user ribsen@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1553 | DUPLICATE_USER | Calling user smckenna@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1569 | DUPLICATE_USER | Calling user scentineo@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |
| D1579 | DUPLICATE_USER | Calling user amaguire@cb231.dc-01.com already exists in Webex | Update existing person (settings only) |

## 5. Batch Execution Order

| Tier | Batch | Operations | Resource Types |
|------|-------|------------|----------------|
| 0 | org-wide | 12 | Location |
| 1 | org-wide | 50 | line_key_template, Operating Mode, Route Group, Trunk |
| 2 | location:DP-ATL-Phones | 45 | Person |
| 2 | location:DP-CHI-Phones | 45 | Person |
| 2 | location:DP-DEN-Phones | 45 | Person |
| 2 | location:DP-NYC-Phones | 45 | Person |
| 2 | location:DP-SJC-Phones | 45 | Person |
| 2 | location:dCloud_DP | 52 | Person |
| 2 | org-wide | 4 | Workspace |
| 3 | location:DP-ATL-Phones | 23 | Device |
| 3 | location:DP-CHI-Phones | 16 | Device |
| 3 | location:DP-DEN-Phones | 20 | Device |
| 3 | location:DP-NYC-Phones | 23 | Device |
| 3 | location:DP-SJC-Phones | 17 | Device |
| 3 | location:dCloud_DP | 2 | Device |
| 3 | org-wide | 4 | Workspace |
| 4 | location:DP-ATL-Phones | 2 | Hunt Group |
| 4 | location:DP-CHI-Phones | 2 | Hunt Group |
| 4 | location:DP-DEN-Phones | 2 | Hunt Group |
| 4 | location:DP-NYC-Phones | 2 | Hunt Group |
| 4 | location:DP-SJC-Phones | 2 | Hunt Group |
| 4 | location:dCloud_DP | 7 | Hunt Group |
| 4 | org-wide | 25 | Auto Attendant, Pickup Group |
| 5 | location:DP-ATL-Phones | 1 | bulk_device_settings |
| 5 | location:DP-CHI-Phones | 1 | bulk_device_settings |
| 5 | location:DP-DEN-Phones | 1 | bulk_device_settings |
| 5 | location:DP-NYC-Phones | 1 | bulk_device_settings |
| 5 | location:DP-SJC-Phones | 1 | bulk_device_settings |
| 5 | location:dCloud_DP | 53 | bulk_device_settings, Person |
| 5 | org-wide | 56 | call_forwarding, Calling Permission, Workspace |
| 6 | org-wide | 275 | Shared Line |
| 7 | location:dCloud_DP | 17 | bulk_line_key_template |
| 8 | location:DP-ATL-Phones | 1 | bulk_rebuild_phones |
| 8 | location:DP-CHI-Phones | 1 | bulk_rebuild_phones |
| 8 | location:DP-DEN-Phones | 1 | bulk_rebuild_phones |
| 8 | location:DP-NYC-Phones | 1 | bulk_rebuild_phones |
| 8 | location:DP-SJC-Phones | 1 | bulk_rebuild_phones |
| 8 | location:dCloud_DP | 1 | bulk_rebuild_phones |

## 6. Estimated Impact

| What Changes | Details |
|-------------|---------|
| Users added | 300 new Webex Calling users |
| Workspaces added | 4 new workspaces |
| Devices provisioned | 1100 devices |
| Licenses consumed | 304 Webex Calling Professional (300 user + 4 workspace) |
| Locations created | 6 new locations |
| Total operations | 902 |
| Estimated API calls | 1930 calls (~20 min at 100 req/min) |

## 7. Rollback Strategy

Execution is tracked per-operation in the migration database. Rollback deletes created resources in reverse dependency order. Use `wxcli cucm rollback` to initiate.

## 8. Approval

Review the plan above. The migration skill will not execute until you confirm.

- [ ] **I approve this deployment plan.** Proceed with execution.
- [ ] **I need changes.** [Describe what to modify]
- [ ] **Cancel.** Do not execute.
