#!/usr/bin/env python3.11
"""Clean the dcloud-fresh migration store before re-execution."""
import sqlite3
import json

DB = "/Users/ahobgood/.wxcli/migrations/dcloud-fresh/migration.db"
con = sqlite3.connect(DB)
con.execute("PRAGMA journal_mode=WAL")
cur = con.cursor()


def section(title):
    print(f"\n=== {title} ===")


# ---------- Issue 5: Trunk names > 24 chars ----------
section("Trunk name truncation")
TRUNK_NAME_FIXES = {
    "trunk:Imagicle_Stonefax_SIP_Trunk": "Imagicle_Stonefax_Trunk",    # 23
    "trunk:dCloud_SIP_Trunk_To_VCS-C":   "dCloud_SIP_VCS-C",            # 16
    "trunk:dCloud_SIP_Trunk_CWMS_5060":  "dCloud_CWMS_5060",            # 16
    "trunk:Imagicle_CallRec_SIP_Trunk":  "Imagicle_CallRec_Trunk",      # 22
}
for cid, new_name in TRUNK_NAME_FIXES.items():
    before = cur.execute(
        "SELECT json_extract(data,'$.name') FROM objects WHERE canonical_id=?", (cid,)
    ).fetchone()
    if not before:
        print(f"  MISS {cid} (not in objects)")
        continue
    cur.execute(
        "UPDATE objects SET data = json_set(data, '$.name', ?) WHERE canonical_id=?",
        (new_name, cid),
    )
    print(f"  {cid}: {before[0]!r} -> {new_name!r}  ({len(new_name)} chars)")

# ---------- Issue 6: Trunk passwords with ? or ! ----------
section("Trunk password scrub (replace ! and ? with x)")
rows = cur.execute(
    """SELECT canonical_id, json_extract(data,'$.password')
       FROM objects WHERE object_type='trunk'
       AND (json_extract(data,'$.password') LIKE '%!%'
         OR json_extract(data,'$.password') LIKE '%?%')"""
).fetchall()
for cid, pw in rows:
    new_pw = pw.replace("!", "x").replace("?", "y")
    cur.execute(
        "UPDATE objects SET data=json_set(data,'$.password',?) WHERE canonical_id=?",
        (new_pw, cid),
    )
    print(f"  {cid}: {pw!r} -> {new_pw!r}")
print(f"  scrubbed {len(rows)} trunk password(s)")

# ---------- Issue 4: Workspace location_canonical_id NULL ----------
section("Workspace location_canonical_id backfill -> location:dCloud_DP")
cur.execute(
    """UPDATE objects
       SET data = json_set(data, '$.location_canonical_id', 'location:dCloud_DP')
       WHERE object_type='workspace'
       AND json_extract(data,'$.location_canonical_id') IS NULL"""
)
print(f"  fixed {cur.rowcount} workspace(s)")

# ---------- Issue 2: Extension backfill for 5 remote location partitions ----------
section("Extension backfill via device_owned_by_user + device_has_dn(ordinal=1)")
PARTITIONS = ["NYC_PT", "CHI_PT", "SJC_PT", "ATL_PT", "DEN_PT"]
total_backfilled = 0
for pt in PARTITIONS:
    suffix = f":{pt}"
    before = cur.execute(
        """SELECT COUNT(*) FROM objects o
           WHERE o.object_type='user'
             AND json_extract(o.data,'$.extension') IS NULL
             AND EXISTS (
               SELECT 1 FROM cross_refs cr_own
               JOIN cross_refs cr_dn
                 ON cr_dn.from_id = cr_own.from_id
                 AND cr_dn.relationship='device_has_dn'
                 AND cr_dn.ordinal=1
               WHERE cr_own.to_id = o.canonical_id
                 AND cr_own.relationship='device_owned_by_user'
                 AND cr_dn.to_id LIKE ?)""",
        (f"%{suffix}",),
    ).fetchone()[0]
    # Update in Python (SQLite UPDATE...FROM works but nested json_set + correlation is clunky).
    users_to_fix = cur.execute(
        """SELECT DISTINCT o.canonical_id, cr_dn.to_id
           FROM objects o
           JOIN cross_refs cr_own ON cr_own.to_id = o.canonical_id
             AND cr_own.relationship='device_owned_by_user'
           JOIN cross_refs cr_dn ON cr_dn.from_id = cr_own.from_id
             AND cr_dn.relationship='device_has_dn'
             AND cr_dn.ordinal=1
           WHERE o.object_type='user'
             AND json_extract(o.data,'$.extension') IS NULL
             AND cr_dn.to_id LIKE ?""",
        (f"%{suffix}",),
    ).fetchall()
    for uid, dn_id in users_to_fix:
        ext = dn_id.replace("dn:", "").replace(suffix, "")
        cur.execute(
            "UPDATE objects SET data=json_set(data,'$.extension',?) WHERE canonical_id=?",
            (ext, uid),
        )
    print(f"  {pt}: backfilled {len(users_to_fix)} user extensions (pending before: {before})")
    total_backfilled += len(users_to_fix)
print(f"  TOTAL extension backfills: {total_backfilled}")

# Any remaining extension-less users (not backfillable) — report
remaining = cur.execute(
    """SELECT COUNT(*) FROM objects
       WHERE object_type='user'
         AND json_extract(data,'$.extension') IS NULL"""
).fetchone()[0]
print(f"  remaining extension-less users after backfill: {remaining}")

# ---------- Issue 3: Mark incompatible SCCP/CTI device ops as skipped ----------
section("Mark INCOMPATIBLE SCCP/CTI device ops so re-run skips them")
# Find device objects classified incompatible (SCCP phones, CTI Ports, Cisco IP Communicator etc.)
incompat = cur.execute(
    """SELECT canonical_id, json_extract(data,'$.model') AS model,
              json_extract(data,'$.cucm_protocol') AS proto
       FROM objects
       WHERE object_type='device'
         AND (json_extract(data,'$.cucm_protocol')='SCCP'
           OR json_extract(data,'$.model') IN ('CTI Port','CTI Route Point','Cisco IP Communicator'))"""
).fetchall()
print(f"  incompatible device objects found: {len(incompat)}")

# ---------- Issue 1: Reset plan_operations for a fresh re-run ----------
section("Reset plan_operations for clean re-run")
# Count pre-reset
pre = cur.execute(
    "SELECT status, COUNT(*) FROM plan_operations GROUP BY status"
).fetchall()
print(f"  pre-reset status distribution: {dict(pre)}")

# Reset ALL ops to pending, clear webex_id and error_message.
cur.execute(
    """UPDATE plan_operations
       SET status='pending',
           webex_id=NULL,
           error_message=NULL,
           completed_at=NULL,
           attempts=0"""
)
print(f"  reset {cur.rowcount} operations to pending")

# Now mark the incompatible device ops as permanently skipped so they never re-execute.
if incompat:
    placeholders = ",".join("?" * len(incompat))
    ids = [c[0] for c in incompat]
    cur.execute(
        f"""UPDATE plan_operations
            SET status='skipped', error_message='device INCOMPATIBLE (SCCP/CTI) — excluded from re-run'
            WHERE resource_type='device' AND canonical_id IN ({placeholders})""",
        ids,
    )
    print(f"  pre-skipped {cur.rowcount} device operations for incompatible devices")

post = cur.execute(
    "SELECT status, COUNT(*) FROM plan_operations GROUP BY status"
).fetchall()
print(f"  post-reset status distribution: {dict(post)}")

con.commit()
con.close()
print("\nDONE. DB cleaned and ready for re-execution.")
