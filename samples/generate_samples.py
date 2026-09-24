"""
Generate realistic *synthetic* classified-style datasets for AetherMask testing.

All content is entirely fictional and generated from a fixed seed. Nothing here
is derived from real operational data.
"""
from __future__ import annotations

import os
import random
from datetime import date, timedelta

import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__))
RNG = random.Random(20260922)

SQUADRONS = ["12th Strike Squadron", "4th Strike Squadron", "77th Strike Squadron",
             "9th Recon Squadron", "23rd Strike Squadron"]
TARGETS = ["Target BASTION", "Target IRONGATE", "Target SEAWALL", "Target REDLINE",
           "Target NORTHPEAK", "Target DEEPWELL"]
CALLSIGNS = ["ALPHA-1", "BRAVO-12", "CHARLIE-7", "DELTA-3", "ECHO-9", "FOXTROT-21",
             "GOLF-4", "HOTEL-15"]
CLASSIFICATIONS = ["TOP SECRET", "SECRET", "CONFIDENTIAL", "SECRET", "SECRET", "CONFIDENTIAL"]
WEAPONS = ["GBU-31 JDAM", "AGM-158 JASSM", "AGM-88 HARM", "GBU-39 SDB", "AGM-114 Hellfire"]
BASES = ["Camp Ridgeway", "Fort Aldergate", "Base Nordhavn", "Airbase Kestrel", "Camp Lindholm"]
THREATS = ["HIGH", "MEDIUM", "LOW", "CRITICAL", "MEDIUM", "HIGH"]
OPERATIONS = ["Operation Nightfall", "Operation Ironbound", "Operation Silverkeep",
              "Operation Tidewatch"]
OFFICERS = ["Col. James Harding", "Maj. Elena Vostrikova", "Capt. Omar Nasser",
            "Lt. Sarah Whitfield", "Cdr. Peter Lindqvist"]
CLEARANCE = ["TS/SCI", "SECRET", "TS/SCI", "SECRET", "CONFIDENTIAL"]


def build_missions(n: int = 420) -> pl.DataFrame:
    rows = []
    d0 = date(2025, 1, 6)
    for i in range(n):
        sq = RNG.choice(SQUADRONS)
        tgt = RNG.choice(TARGETS)
        cs = RNG.choice(CALLSIGNS)
        rows.append({
            "mission_id": f"MSN-{4000 + i}",
            "operation_name": RNG.choice(OPERATIONS),
            "strike_squadron": sq,
            "callsign": cs,
            "target_designation": tgt,
            "target_latitude": round(RNG.uniform(34.0, 41.5), 5),
            "target_longitude": round(RNG.uniform(-119.0, -102.0), 5),
            "launch_time": d0 + timedelta(days=i % 180),
            "weapon_system": RNG.choice(WEAPONS),
            "warhead_yield_kg": RNG.choice([227, 454, 113, 908, 45]),
            "sorties_flown": RNG.randint(1, 8),
            "kill_probability": round(RNG.uniform(0.55, 0.98), 3),
            "threat_level": RNG.choice(THREATS),
            "classification": RNG.choice(CLASSIFICATIONS),
            "base_id": f"BASE-{RNG.randint(1, 5):02d}",
            "fuel_burn_kg": round(RNG.uniform(1800, 9400), 1),
            "mission_notes": RNG.choice([
                f"{RNG.choice(OFFICERS)} authorised the strike package against {tgt}.",
                f"Callsign {cs} egressed via corridor south of {RNG.choice(BASES)}.",
                f"{RNG.choice(OPERATIONS)} tasking confirmed by {RNG.choice(OFFICERS)}.",
                f"Battle damage assessment pending for {tgt}; contact ops@defnet.mil.",
            ]),
        })
    return pl.DataFrame(rows)


def build_bases() -> pl.DataFrame:
    rows = []
    for i in range(1, 6):
        rows.append({
            "base_id": f"BASE-{i:02d}",
            "installation_name": BASES[i - 1],
            "theater": RNG.choice(["EUCOM", "INDOPACOM", "CENTCOM"]),
            "runway_length_m": RNG.choice([2400, 3050, 3600, 2750, 4000]),
            "personnel_assigned": RNG.randint(420, 3800),
            "clearance_required": RNG.choice(CLEARANCE),
        })
    return pl.DataFrame(rows)


def build_personnel(n: int = 140) -> pl.DataFrame:
    rows = []
    for i in range(n):
        rows.append({
            "service_number": f"SN-{90000 + i}",
            "full_name": RNG.choice(OFFICERS),
            "rank": RNG.choice(["Colonel", "Major", "Captain", "Lieutenant", "Commander"]),
            "strike_squadron": RNG.choice(SQUADRONS),
            "clearance_level": RNG.choice(CLEARANCE),
            "base_id": f"BASE-{RNG.randint(1, 5):02d}",
            "annual_flight_hours": RNG.randint(90, 720),
            "email": f"user{i}@defnet.mil",
        })
    return pl.DataFrame(rows)


def main() -> None:
    missions = build_missions()
    bases = build_bases()
    personnel = build_personnel()

    missions.write_csv(os.path.join(HERE, "classified_missions.csv"))
    bases.write_csv(os.path.join(HERE, "classified_bases.csv"))
    personnel.write_csv(os.path.join(HERE, "classified_personnel.csv"))
    missions.write_parquet(os.path.join(HERE, "classified_missions.parquet"))

    # Multi-sheet workbook with a formula
    from openpyxl import Workbook
    wb = Workbook()
    wb.remove(wb.active)
    for sheet, df in (("Missions", missions.head(120)), ("Bases", bases), ("Personnel", personnel.head(60))):
        ws = wb.create_sheet(sheet)
        ws.append(list(df.columns))
        for r in df.iter_rows():
            ws.append([v.isoformat() if hasattr(v, "isoformat") else v for v in r])
    ws = wb["Bases"]
    ws["H1"] = "total_personnel"
    ws["H2"] = "=SUM(E2:E6)"
    wb.save(os.path.join(HERE, "classified_workbook.xlsx"))

    # PostgreSQL-style dump
    lines = [
        "-- Synthetic classified dump for AetherMask testing",
        "CREATE TABLE bases (",
        "  base_id text NOT NULL,",
        "  installation_name text,",
        "  theater text,",
        "  runway_length_m integer,",
        "  personnel_assigned integer,",
        "  clearance_required text",
        ");",
        "",
        "COPY bases (base_id, installation_name, theater, runway_length_m, personnel_assigned, clearance_required) FROM stdin;",
    ]
    for r in bases.iter_rows(named=True):
        lines.append("\t".join(str(r[c]) for c in bases.columns))
    lines.append("\\.")
    lines.append("")
    lines.append("CREATE TABLE strike_log (")
    lines.append("  mission_id text, target_designation text, threat_level text, sorties_flown integer")
    lines.append(");")
    vals = []
    for r in missions.head(40).iter_rows(named=True):
        vals.append(
            "('{}', '{}', '{}', {})".format(
                r["mission_id"], r["target_designation"], r["threat_level"], r["sorties_flown"]
            )
        )
    lines.append(
        "INSERT INTO strike_log (mission_id, target_designation, threat_level, sorties_flown) VALUES\n"
        + ",\n".join(vals) + ";"
    )
    with open(os.path.join(HERE, "classified_dump.sql"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"missions  : {missions.height} rows x {missions.width} cols")
    print(f"bases     : {bases.height} rows")
    print(f"personnel : {personnel.height} rows")
    print("Wrote CSV, Parquet, XLSX and SQL samples to", HERE)


if __name__ == "__main__":
    main()
