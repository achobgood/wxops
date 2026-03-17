"""Live test v2 write commands against Webex API.

Runs all create → verify → update → verify → delete → verify cycles.
Uses a single API session to avoid rate limiting.
"""
import sys
import time
from datetime import date

from wxc_sdk.rest import RestError
from wxc_sdk.common.schedules import Schedule, Event, ScheduleType
from wxc_sdk.telephony.autoattendant import (
    AutoAttendant, AutoAttendantMenu, Greeting,
    AutoAttendantKeyConfiguration, AutoAttendantAction,
)
from wxc_sdk.telephony.huntgroup import HuntGroup
from wxc_sdk.telephony.callqueue import CallQueue
from wxc_sdk.telephony.callpark import CallPark
from wxc_sdk.telephony.callpickup import CallPickup
from wxc_sdk.telephony.paging import Paging
from wxc_sdk.telephony.voicemail_groups import VoicemailGroupDetail

from wxcli.auth import get_api

LOC = "Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OL2MxODNmYTVmLTI2MGYtNDdiZS04YjE0LTEyODQ5Y2RlNzFlNQ"

PASS = 0
FAIL = 0
BUGS = []


def ok(msg):
    global PASS
    PASS += 1
    print(f"  PASS: {msg}")


def fail(msg, err=None):
    global FAIL
    FAIL += 1
    detail = f" — {err}" if err else ""
    print(f"  FAIL: {msg}{detail}")
    BUGS.append(f"{msg}{detail}")


def section(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


def test_auto_attendants(api):
    section("AUTO ATTENDANTS")

    # Need a schedule first
    sched = Schedule(name="test-aa-sched", schedule_type=ScheduleType.business_hours)
    sched_id = api.telephony.schedules.create(obj_id=LOC, schedule=sched)
    print(f"  (created prerequisite schedule: {sched_id})")

    # CREATE
    default_key = AutoAttendantKeyConfiguration(key="0", action=AutoAttendantAction.exit)
    default_menu = AutoAttendantMenu(
        greeting=Greeting.default,
        extension_enabled=True,
        key_configurations=[default_key],
    )
    settings = AutoAttendant(
        name="test-aa-live",
        extension="9902",
        enabled=True,
        business_hours_menu=default_menu,
        after_hours_menu=default_menu,
        business_schedule="test-aa-sched",
    )
    try:
        aa_id = api.telephony.auto_attendant.create(location_id=LOC, settings=settings)
        ok(f"create → {aa_id[:30]}...")
    except Exception as e:
        fail("create", e)
        return

    time.sleep(1)

    # SHOW
    try:
        aa = api.telephony.auto_attendant.details(location_id=LOC, auto_attendant_id=aa_id)
        if aa.name == "test-aa-live":
            ok("show → name matches")
        else:
            fail(f"show → name mismatch: {aa.name}")
    except Exception as e:
        fail("show", e)

    # UPDATE
    try:
        aa.name = "test-aa-renamed"
        api.telephony.auto_attendant.update(location_id=LOC, auto_attendant_id=aa_id, settings=aa)
        ok("update → no error")
        aa2 = api.telephony.auto_attendant.details(location_id=LOC, auto_attendant_id=aa_id)
        if aa2.name == "test-aa-renamed":
            ok("update → name verified")
        else:
            fail(f"update → name mismatch: {aa2.name}")
    except Exception as e:
        fail("update", e)

    # DELETE
    try:
        api.telephony.auto_attendant.delete_auto_attendant(location_id=LOC, auto_attendant_id=aa_id)
        ok("delete → no error")
    except Exception as e:
        fail("delete", e)

    # Verify gone
    try:
        aas = list(api.telephony.auto_attendant.list(location_id=LOC, name="test-aa-renamed"))
        if len(aas) == 0:
            ok("delete → verified gone")
        else:
            fail("delete → still exists")
    except Exception as e:
        fail("delete verify", e)

    # Cleanup schedule
    try:
        scheds = list(api.telephony.schedules.list(obj_id=LOC, name="test-aa-sched"))
        if scheds:
            api.telephony.schedules.delete_schedule(
                obj_id=LOC,
                schedule_type=ScheduleType.business_hours,
                schedule_id=scheds[0].schedule_id,
            )
    except Exception:
        pass


def test_hunt_groups(api):
    section("HUNT GROUPS")

    # CREATE
    settings = HuntGroup(name="test-hg-live", extension="9903", enabled=True)
    try:
        hg_id = api.telephony.huntgroup.create(location_id=LOC, settings=settings)
        ok(f"create → {hg_id[:30]}...")
    except Exception as e:
        fail("create", e)
        return

    time.sleep(1)

    # SHOW
    try:
        hg = api.telephony.huntgroup.details(location_id=LOC, huntgroup_id=hg_id)
        if hg.name == "test-hg-live":
            ok("show → name matches")
        else:
            fail(f"show → name mismatch: {hg.name}")
    except Exception as e:
        fail("show", e)

    # UPDATE
    try:
        hg.name = "test-hg-renamed"
        api.telephony.huntgroup.update(location_id=LOC, huntgroup_id=hg_id, update=hg)
        ok("update → no error")
        hg2 = api.telephony.huntgroup.details(location_id=LOC, huntgroup_id=hg_id)
        if hg2.name == "test-hg-renamed":
            ok("update → name verified")
        else:
            fail(f"update → name mismatch: {hg2.name}")
    except Exception as e:
        fail("update", e)

    # DELETE
    try:
        api.telephony.huntgroup.delete_huntgroup(location_id=LOC, huntgroup_id=hg_id)
        ok("delete → no error")
        hgs = list(api.telephony.huntgroup.list(location_id=LOC, name="test-hg-renamed"))
        if len(hgs) == 0:
            ok("delete → verified gone")
        else:
            fail("delete → still exists")
    except Exception as e:
        fail("delete", e)


def test_call_queues(api):
    section("CALL QUEUES")

    from wxc_sdk.telephony.callqueue import CallQueueCallPolicies, CQRoutingType
    from wxc_sdk.telephony.hg_and_cq import Policy

    # CREATE — API requires callPolicies
    call_policies = CallQueueCallPolicies(
        routing_type=CQRoutingType.priority_based,
        policy=Policy.circular,
    )
    settings = CallQueue(name="test-cq-live", extension="9904", call_policies=call_policies)
    try:
        cq_id = api.telephony.callqueue.create(location_id=LOC, settings=settings)
        ok(f"create → {cq_id[:30]}...")
    except Exception as e:
        fail("create", e)
        return

    time.sleep(1)

    # SHOW
    try:
        cq = api.telephony.callqueue.details(location_id=LOC, queue_id=cq_id)
        if cq.name == "test-cq-live":
            ok("show → name matches")
        else:
            fail(f"show → name mismatch: {cq.name}")
    except Exception as e:
        fail("show", e)

    # UPDATE — use partial object, not full details (callingLineIdPolicy issue)
    try:
        upd = CallQueue(name="test-cq-renamed")
        api.telephony.callqueue.update(location_id=LOC, queue_id=cq_id, update=upd)
        ok("update → no error")
        cq2 = api.telephony.callqueue.details(location_id=LOC, queue_id=cq_id)
        if cq2.name == "test-cq-renamed":
            ok("update → name verified")
        else:
            fail(f"update → name mismatch: {cq2.name}")
    except Exception as e:
        fail("update", e)

    # AVAILABLE AGENTS
    try:
        agents = list(api.telephony.callqueue.available_agents(location_id=LOC))
        ok(f"available-agents → {len(agents)} agents")
    except Exception as e:
        fail("available-agents", e)

    # DELETE
    try:
        api.telephony.callqueue.delete_queue(location_id=LOC, queue_id=cq_id)
        ok("delete → no error")
        cqs = list(api.telephony.callqueue.list(location_id=LOC, name="test-cq-renamed"))
        if len(cqs) == 0:
            ok("delete → verified gone")
        else:
            fail("delete → still exists")
    except Exception as e:
        fail("delete", e)


def test_call_park(api):
    section("CALL PARK")

    from wxc_sdk.telephony.callpark import RecallHuntGroup, CallParkRecall

    # Cleanup leftovers from previous runs
    for p in list(api.telephony.callpark.list(location_id=LOC)):
        if p.name.startswith("test-cp-"):
            api.telephony.callpark.delete_callpark(location_id=LOC, callpark_id=p.callpark_id)

    # CREATE — API requires recall option
    recall = RecallHuntGroup(option=CallParkRecall.parking_user_only)
    settings = CallPark(name="test-cp-live", recall=recall)
    try:
        cp_id = api.telephony.callpark.create(location_id=LOC, settings=settings)
        ok(f"create → {cp_id[:30]}...")
    except Exception as e:
        fail("create", e)
        return

    time.sleep(1)

    try:
        cp = api.telephony.callpark.details(location_id=LOC, callpark_id=cp_id)
        if cp.name == "test-cp-live":
            ok("show → name matches")
        else:
            fail(f"show → name mismatch: {cp.name}")
    except Exception as e:
        fail("show", e)

    try:
        upd = CallPark(name="test-cp-renamed")
        api.telephony.callpark.update(location_id=LOC, callpark_id=cp_id, settings=upd)
        ok("update → no error")
    except Exception as e:
        fail("update", e)

    try:
        api.telephony.callpark.delete_callpark(location_id=LOC, callpark_id=cp_id)
        ok("delete → no error")
    except Exception as e:
        fail("delete", e)


def test_call_pickup(api):
    section("CALL PICKUP")

    # Cleanup leftovers from previous runs
    for p in list(api.telephony.pickup.list(location_id=LOC)):
        if p.name.startswith("test-pu-"):
            api.telephony.pickup.delete_pickup(location_id=LOC, pickup_id=p.pickup_id)

    settings = CallPickup(name="test-pu-live")
    try:
        pu_id = api.telephony.pickup.create(location_id=LOC, settings=settings)
        ok(f"create → {pu_id[:30]}...")
    except Exception as e:
        fail("create", e)
        return

    time.sleep(1)

    try:
        pu = api.telephony.pickup.details(location_id=LOC, pickup_id=pu_id)
        if pu.name == "test-pu-live":
            ok("show → name matches")
        else:
            fail(f"show → name mismatch: {pu.name}")
    except Exception as e:
        fail("show", e)

    try:
        upd = CallPickup(name="test-pu-renamed")
        api.telephony.pickup.update(location_id=LOC, pickup_id=pu_id, settings=upd)
        ok("update → no error")
    except Exception as e:
        fail("update", e)

    try:
        api.telephony.pickup.delete_pickup(location_id=LOC, pickup_id=pu_id)
        ok("delete → no error")
    except Exception as e:
        fail("delete", e)


def test_paging(api):
    section("PAGING")

    settings = Paging(name="test-pg-live", extension="9905", enabled=True)
    try:
        pg_id = api.telephony.paging.create(location_id=LOC, settings=settings)
        ok(f"create → {pg_id[:30]}...")
    except Exception as e:
        fail("create", e)
        return

    time.sleep(1)

    try:
        pg = api.telephony.paging.details(location_id=LOC, paging_id=pg_id)
        if pg.name == "test-pg-live":
            ok("show → name matches")
        else:
            fail(f"show → name mismatch: {pg.name}")
    except Exception as e:
        fail("show", e)

    try:
        pg.name = "test-pg-renamed"
        api.telephony.paging.update(location_id=LOC, update=pg, paging_id=pg_id)
        ok("update → no error (keyword args)")
    except Exception as e:
        fail("update", e)

    try:
        api.telephony.paging.delete_paging(location_id=LOC, paging_id=pg_id)
        ok("delete → no error")
    except Exception as e:
        fail("delete", e)


def test_voicemail_groups(api):
    section("VOICEMAIL GROUPS")

    settings = VoicemailGroupDetail(
        name="test-vg-live", extension="9906", enabled=True,
        passcode="740384", language_code="en_us",
    )
    try:
        # Workaround: wxc_sdk for_create() missing by_alias=True (sends language_code not languageCode)
        from wxc_sdk.common import (VoicemailMessageStorage, StorageType, VoicemailNotifications,
                                     VoicemailFax, VoicemailTransferToNumber, VoicemailCopyOfMessage)
        settings.message_storage = VoicemailMessageStorage(storage_type=StorageType.internal)
        settings.notifications = VoicemailNotifications(enabled=False)
        settings.fax_message = VoicemailFax(enabled=False)
        settings.transfer_to_number = VoicemailTransferToNumber(enabled=False)
        settings.email_copy_of_message = VoicemailCopyOfMessage(enabled=False)
        body = settings.model_dump(mode='json', exclude_unset=True, by_alias=True,
            include={'name', 'phone_number', 'extension', 'first_name', 'last_name', 'passcode',
                     'language_code', 'message_storage', 'notifications', 'fax_message',
                     'transfer_to_number', 'email_copy_of_message'})
        url = api.telephony.voicemail_groups.ep(LOC)
        data = api.telephony.voicemail_groups.post(url=url, json=body)
        vg_id = data['id']
        ok(f"create → {vg_id[:30]}...")
    except Exception as e:
        fail("create", e)
        return

    time.sleep(1)

    try:
        vg = api.telephony.voicemail_groups.details(location_id=LOC, voicemail_group_id=vg_id)
        if vg.name == "test-vg-live":
            ok("show → name matches")
        else:
            fail(f"show → name mismatch: {vg.name}")
    except Exception as e:
        fail("show", e)

    try:
        vg.name = "test-vg-renamed"
        api.telephony.voicemail_groups.update(
            location_id=LOC, voicemail_group_id=vg_id, settings=vg,
        )
        ok("update → no error")
    except Exception as e:
        fail("update", e)

    try:
        api.telephony.voicemail_groups.delete(location_id=LOC, voicemail_group_id=vg_id)
        ok("delete → no error")
    except Exception as e:
        fail("delete", e)


def test_operating_modes(api):
    section("OPERATING MODES")

    from wxc_sdk.telephony.operating_modes import OperatingMode, OperatingModeHoliday, OperatingModeSchedule
    from wxc_sdk.common.schedules import ScheduleLevel

    from wxc_sdk.telephony.operating_modes import SameHoursDaily, DaySchedule
    settings = OperatingMode(
        name="test-om-live",
        type=OperatingModeSchedule.same_hours_daily,
        level=ScheduleLevel.organization,
        same_hours_daily=SameHoursDaily(
            monday_to_friday=DaySchedule(enabled=True, all_day_enabled=True),
            saturday_to_sunday=DaySchedule(enabled=False),
        ),
    )
    try:
        om_id = api.telephony.operating_modes.create(settings=settings)
        ok(f"create → {om_id[:30]}...")
    except Exception as e:
        fail("create", e)
        return

    time.sleep(1)

    try:
        om = api.telephony.operating_modes.details(mode_id=om_id)
        if om.name == "test-om-live":
            ok("show → name matches")
        else:
            fail(f"show → name mismatch: {om.name}")
    except Exception as e:
        fail("show", e)

    try:
        om.name = "test-om-renamed"
        api.telephony.operating_modes.update(mode_id=om_id, settings=om)
        ok("update → no error")
    except Exception as e:
        fail("update", e)

    # Clean up the sameHoursDaily mode
    try:
        api.telephony.operating_modes.delete(mode_id=om_id)
        ok("delete → cleaned up sameHoursDaily mode")
    except Exception as e:
        fail("delete", e)

    # ADD HOLIDAY — requires a HOLIDAY type operating mode
    holiday_mode = OperatingMode(
        name="test-om-holiday",
        type=OperatingModeSchedule.holiday,
        level=ScheduleLevel.organization,
        holidays=[OperatingModeHoliday(
            name="Christmas", start_date=date(2026, 12, 25), end_date=date(2026, 12, 25),
            all_day_enabled=True,
        )],
    )
    try:
        hom_id = api.telephony.operating_modes.create(settings=holiday_mode)
        ok(f"create holiday mode → {hom_id[:30]}...")
    except Exception as e:
        fail("create holiday mode", e)
        return

    try:
        holiday = OperatingModeHoliday(
            name="Test Holiday", start_date=date(2026, 12, 25), end_date=date(2026, 12, 25),
            all_day_enabled=True,
        )
        h_id = api.telephony.operating_modes.holiday_create(mode_id=hom_id, settings=holiday)
        ok(f"add-holiday → {h_id}")
    except Exception as e:
        fail("add-holiday", e)
        h_id = None

    # DELETE HOLIDAY
    if h_id:
        try:
            api.telephony.operating_modes.holiday_delete(mode_id=hom_id, holiday_id=h_id)
            ok("delete-holiday → no error")
        except Exception as e:
            fail("delete-holiday", e)

    # Clean up holiday mode
    try:
        api.telephony.operating_modes.delete(mode_id=hom_id)
        ok("delete → cleaned up holiday mode")
    except Exception as e:
        fail("delete holiday mode", e)


if __name__ == "__main__":
    print("Initializing API...")
    api = get_api()
    print(f"Testing against location: test-z100 ({LOC[:30]}...)")
    print(f"Started at: {time.strftime('%H:%M:%S')}")

    test_auto_attendants(api)
    test_hunt_groups(api)
    test_call_queues(api)
    test_call_park(api)
    test_call_pickup(api)
    test_paging(api)
    test_voicemail_groups(api)
    test_operating_modes(api)

    print(f"\n{'='*60}")
    print(f"  RESULTS: {PASS} passed, {FAIL} failed")
    print(f"{'='*60}")

    if BUGS:
        print("\nBUGS FOUND:")
        for b in BUGS:
            print(f"  - {b}")

    sys.exit(1 if FAIL > 0 else 0)
