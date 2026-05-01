"""build_14floor_stairs.py

Constructs the 14-floor SandboxSmall stair architecture:
  - Adds 6 new chapter rows for the missing floors (Lv-5..Lv-7, D-5..D-7)
  - Adds 8 stair landmarks following the vanilla SS pattern
  - Adds 8 stair zones (one per stair landmark) with primary + addl chapters
  - Adds StringTable entries for new chapter / landmark display names
  - Syncs every NameMap, NamesReferencedFromExportDataCount, and Generations[0].NameCount

The four touched JSONs:
  experiments/worldgen_research/DT_Moria_Chapters.json
  experiments/worldgen_research/DT_Moria_Landmarks.json
  experiments/worldgen_research/DT_Moria_Zones.json
  experiments/worldgen_research/World.json

This script preserves vanilla rows untouched. It only APPENDS the new rows
after the existing rows in each table.
"""
from __future__ import annotations
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\johnb\OneDrive\Documents\Projects\Moria-Replication\experiments\worldgen_research")
CHAPTERS_FP = ROOT / "DT_Moria_Chapters.json"
LANDMARKS_FP = ROOT / "DT_Moria_Landmarks.json"
ZONES_FP = ROOT / "DT_Moria_Zones.json"
WORLD_FP = ROOT / "World.json"

# ---- Plan tables -----------------------------------------------------------

# 6 new chapter rows: name, layer, ChapterID, ESL, MinZ=MaxZ=PrimeZ, displayKey, displayValue
NEW_CHAPTERS = [
    # name,                        layer, chapId, esl, z, key,                            value
    ("SandboxSmall-chapter-9",       4,   9,   4, 23, "Chapter.Sandbox.Level5.Name",  "The Fifth Level"),
    ("SandboxSmall-chapter-10",      5,   10,  5, 27, "Chapter.Sandbox.Level6.Name",  "The Sixth Level"),
    ("SandboxSmall-chapter-11",      6,   11,  6, 28, "Chapter.Sandbox.Level7.Name",  "The Seventh Level"),
    ("SandboxSmall-chapter-12",     -5,   12,  5,  4, "Chapter.Sandbox.Deep5.Name",   "The Fifth Deep"),
    ("SandboxSmall-chapter-13",     -6,   13,  6,  1, "Chapter.Sandbox.Deep6.Name",   "The Sixth Deep"),
    ("SandboxSmall-chapter-14",     -7,   14,  7,  0, "Chapter.Sandbox.Deep7.Name",   "The Seventh Deep"),
]

# 8 stair plan
# fields: short_name (for landmark + zone), primary_chap, addl_chaps,
#   bp_z, ts_z, bp_x, bp_y, bubble_template
STAIRS = [
    ("TopAscent",     "SandboxSmall-chapter-11", ["SandboxSmall-chapter-10"],                            28, 2, 10,  4, "BB_Sandbox_Elevator_Urban"),
    ("UpperAscent",   "SandboxSmall-chapter-10", ["SandboxSmall-chapter-11", "SandboxSmall-chapter-9"],  27, 2, 10,  8, "BB_Sandbox_Elevator_Urban"),
    ("HighAscent",    "SandboxSmall-chapter-9",  ["SandboxSmall-chapter-10", "SandboxSmall-chapter-4"],  23, 4, 10, 12, "BB_Sandbox_Elevator_Urban"),
    ("MidAscent",     "SandboxSmall-chapter-3",  ["SandboxSmall-chapter-4", "SandboxSmall-chapter-2"],   21, 4, 10, 16, "BB_Sandbox_Elevator_Urban"),
    ("GroundStair",   "SandboxSmall-chapter-1",  ["SandboxSmall-chapter-2", "SandboxSmall-chapter-5"],   18, 2, 10, 20, "BB_Sandbox_Elevator_Urban"),
    ("UpperDescent",  "SandboxSmall-chapter-6",  ["SandboxSmall-chapter-5", "SandboxSmall-chapter-7"],   13, 4, 10, 24, "BB_Sandbox_CrystalDescent"),
    ("MidDescent",    "SandboxSmall-chapter-8",  ["SandboxSmall-chapter-7", "SandboxSmall-chapter-12"],   8, 4, 14,  4, "BB_Sandbox_CrystalDescent"),
    ("LowerDescent",  "SandboxSmall-chapter-13", ["SandboxSmall-chapter-12", "SandboxSmall-chapter-14"],  1, 3, 14,  8, "BB_Sandbox_CrystalDescent"),
]

# ---- Helpers ---------------------------------------------------------------

def load(fp):
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)

def save(fp, data):
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_to_namemap(data, names):
    """Append unique names to NameMap if missing. Returns count added."""
    nm = data.get("NameMap", [])
    added = 0
    seen = set(nm)
    for n in names:
        if n not in seen:
            nm.append(n)
            seen.add(n)
            added += 1
    return added

def sync_counters(data):
    n = len(data["NameMap"])
    data["NamesReferencedFromExportDataCount"] = n
    g = data.get("Generations") or []
    if g and isinstance(g[0], dict):
        g[0]["NameCount"] = n

def fp(values, name):
    for p in values or []:
        if isinstance(p, dict) and p.get("Name") == name:
            return p
    return None

def set_int(values, name, v):
    p = fp(values, name)
    if p is not None:
        p["Value"] = v

def set_enum(values, name, v):
    p = fp(values, name)
    if p is not None:
        p["Value"] = v

def set_text_displayname(values, key):
    p = fp(values, "DisplayName")
    if p is not None:
        p["Value"] = key

# ---- Phase 1: chapters -----------------------------------------------------

def build_chapter_rows(chapters_data):
    rows = chapters_data["Exports"][0]["Table"]["Data"]
    # Find SandboxSmall-chapter-1 as the clone template
    template = None
    for r in rows:
        if r.get("Name") == "SandboxSmall-chapter-1":
            template = r
            break
    if template is None:
        raise SystemExit("SandboxSmall-chapter-1 template not found")

    new_names = []
    for name, layer, chap_id, esl, z, key, value in NEW_CHAPTERS:
        nr = copy.deepcopy(template)
        nr["Name"] = name
        v = nr["Value"]
        set_int(v, "ChapterID", chap_id)
        set_int(v, "Layer", layer)
        set_int(v, "EnemyScalingLevel", esl)
        set_int(v, "MinZ", z)
        set_int(v, "MaxZ", z)
        set_int(v, "PrimeZ", z)
        set_text_displayname(v, key)
        rows.append(nr)
        new_names.append(name)
    return new_names

# ---- Phase 2a: landmarks ---------------------------------------------------

def build_landmark_rows(landmarks_data):
    rows = landmarks_data["Exports"][0]["Table"]["Data"]
    # Use Sandbox.FirstStair as the clone template
    template = None
    for r in rows:
        if r.get("Name") == "Sandbox.FirstStair":
            template = r
            break
    if template is None:
        raise SystemExit("Sandbox.FirstStair template not found")

    new_lm_names = []
    new_string_keys = []
    for short_name, prim, addl, bp_z, ts_z, bp_x, bp_y, bubble in STAIRS:
        lm_name = f"Sandbox.{short_name}"
        display_key = f"Landmarks.Sandbox.{short_name}"
        tag_name = f"World.Landmark.{lm_name}"

        nr = copy.deepcopy(template)
        nr["Name"] = lm_name
        v = nr["Value"]

        # Placement = Fixed (already)
        set_enum(v, "Placement", "ELandmarkPlacement::Fixed")

        # BasePosition
        bp = fp(v, "BasePosition")
        bp_inner = bp["Value"][0]["Value"]
        bp_inner["X"] = bp_x
        bp_inner["Y"] = bp_y
        bp_inner["Z"] = bp_z

        # InternalId TagName
        iid = fp(v, "InternalId")
        iid_inner = iid["Value"][0]
        iid_inner["Value"] = tag_name

        # BaseBubbleName
        bbn = fp(v, "BaseBubbleName")
        bbn["Value"] = bubble

        # DisplayName -> StringTableEntry pointing to new key
        dn = fp(v, "DisplayName")
        dn["Value"] = display_key
        # Ensure HistoryType + TableId are correct (template already has them)
        dn["HistoryType"] = "StringTableEntry"
        dn["TableId"] = "/Game/Tech/Data/StringTables/World.World"

        # GuaranteedConnections: empty (template already empty)
        gc = fp(v, "GuaranteedConnections")
        gc["Value"] = []

        # bPlayerStartLocation false, ChallengeRating 0 (template already)
        bpsl = fp(v, "bPlayerStartLocation")
        bpsl["Value"] = False
        cr = fp(v, "ChallengeRating")
        cr["Value"] = 0

        # EnabledState Live (template already)
        set_enum(v, "EnabledState", "ERowEnabledState::Live")

        rows.append(nr)
        new_lm_names.append(lm_name)
        new_string_keys.append((display_key, f"{short_name} Stair"))
    return new_lm_names, new_string_keys

# ---- Phase 2b: zones -------------------------------------------------------

def build_zone_rows(zones_data):
    rows = zones_data["Exports"][0]["Table"]["Data"]
    # Use Sandbox_Small_Elevator_C as the clone template
    template = None
    for r in rows:
        if r.get("Name") == "Sandbox_Small_Elevator_C":
            template = r
            break
    if template is None:
        raise SystemExit("Sandbox_Small_Elevator_C template not found")

    new_zone_names = []
    new_lm_names_referenced = []
    for short_name, prim, addl, bp_z, ts_z, bp_x, bp_y, bubble in STAIRS:
        zone_name = f"Sandbox_Small_Elevator_{short_name}"
        lm_name = f"Sandbox.{short_name}"

        nr = copy.deepcopy(template)
        nr["Name"] = zone_name
        v = nr["Value"]

        # Position (0,0,0)
        pos = fp(v, "Position")
        pinner = pos["Value"][0]["Value"]
        pinner["X"] = 0; pinner["Y"] = 0; pinner["Z"] = 0

        # TargetSize -> (6,6,ts_z)
        ts = fp(v, "TargetSize")
        tinner = ts["Value"][0]["Value"]
        tinner["X"] = 6; tinner["Y"] = 6; tinner["Z"] = ts_z

        # bPositionFromLandmarks/ZoneTable
        flm = fp(v, "bPositionFromLandmarks")
        flm["Value"] = True
        fzt = fp(v, "bPositionFromZoneTable")
        fzt["Value"] = True

        # bExtendFootprint=true (per spec)
        bef = fp(v, "bExtendFootprint")
        if bef is not None:
            bef["Value"] = True

        # PreferredZOverride = -1
        pzo = fp(v, "PreferredZOverride")
        if pzo is not None:
            pzo["Value"] = -1

        # Chapter -> primary
        chap = fp(v, "Chapter")
        # Chapter is a struct with RowName
        chap_inner = chap["Value"]
        # find RowName entry
        for prop in chap_inner:
            if isinstance(prop, dict) and prop.get("Name") == "RowName":
                prop["Value"] = prim
                break

        # AdditionalChapters -> array of struct{RowName=...}
        achap = fp(v, "AdditionalChapters")
        # Build new entries by cloning the existing entries' shape
        if achap.get("Value"):
            shape = copy.deepcopy(achap["Value"][0])
        else:
            # Fallback shape — won't normally hit since template has 2 entries
            shape = None
        new_entries = []
        for a in addl:
            if shape is None: break
            entry = copy.deepcopy(shape)
            inner = entry.get("Value")
            if isinstance(inner, list):
                for prop in inner:
                    if isinstance(prop, dict) and prop.get("Name") == "RowName":
                        prop["Value"] = a
                        break
            new_entries.append(entry)
        achap["Value"] = new_entries

        # LandmarkHandles -> ONE entry with Landmark.RowName=lm_name, Placement=Fixed, ext=true
        lh = fp(v, "LandmarkHandles")
        if lh and lh.get("Value"):
            shape_lh = copy.deepcopy(lh["Value"][0])
            # mutate
            inner = shape_lh.get("Value")
            if isinstance(inner, list):
                for prop in inner:
                    if not isinstance(prop, dict):
                        continue
                    pname = prop.get("Name")
                    if pname == "Landmark":
                        # nested struct with RowName
                        sub = prop.get("Value")
                        if isinstance(sub, list):
                            for s in sub:
                                if isinstance(s, dict) and s.get("Name") == "RowName":
                                    s["Value"] = lm_name
                    elif pname == "Placement":
                        prop["Value"] = "ELandmarkPlacement::Fixed"
                    elif pname == "bExtendedConnectivityLandmark":
                        prop["Value"] = True
            lh["Value"] = [shape_lh]

        # EnabledState Live (template already)
        set_enum(v, "EnabledState", "ERowEnabledState::Live")

        rows.append(nr)
        new_zone_names.append(zone_name)
        new_lm_names_referenced.append(lm_name)
    return new_zone_names, new_lm_names_referenced

# ---- Phase 3: World.json string table --------------------------------------

def add_stringtable_entries(world_data, entries):
    table = world_data["Exports"][0]["Table"]["Value"]
    existing = {pair[0] for pair in table if isinstance(pair, list) and len(pair) >= 1}
    added = 0
    for k, v in entries:
        if k in existing:
            continue
        table.append([k, v])
        existing.add(k)
        added += 1
    return added

# ---- Main ------------------------------------------------------------------

def main():
    print("Loading data...")
    chapters = load(CHAPTERS_FP)
    landmarks = load(LANDMARKS_FP)
    zones = load(ZONES_FP)
    world = load(WORLD_FP)

    # Phase 1: chapters
    print("\n[Phase 1] Adding 6 chapter rows...")
    new_chap_names = build_chapter_rows(chapters)
    print(f"  Added: {new_chap_names}")
    # NameMap entries needed: chapter names, the new DisplayName keys
    chap_namemap_adds = list(new_chap_names) + [t[5] for t in NEW_CHAPTERS]
    nadded = add_to_namemap(chapters, chap_namemap_adds)
    print(f"  Chapters NameMap +{nadded}")
    sync_counters(chapters)

    # Phase 2a: landmarks
    print("\n[Phase 2a] Adding 8 stair landmarks...")
    new_lm_names, new_str_keys = build_landmark_rows(landmarks)
    print(f"  Added landmarks: {new_lm_names}")
    # NameMap adds: landmark row names, BBN values, tag names, displaykey strings
    lm_namemap_adds = list(new_lm_names)
    # Add bubble names (some already present)
    for s in STAIRS:
        lm_namemap_adds.append(s[7])  # bubble
    # Add tag names
    for ln in new_lm_names:
        lm_namemap_adds.append(f"World.Landmark.{ln}")
    # The displayKey strings are stored as TextProperty Value (string), not FName
    # but to be safe include them
    for k, _ in new_str_keys:
        lm_namemap_adds.append(k)
    nadded_lm = add_to_namemap(landmarks, lm_namemap_adds)
    print(f"  Landmarks NameMap +{nadded_lm}")
    sync_counters(landmarks)

    # Phase 2b: zones
    print("\n[Phase 2b] Adding 8 stair zones...")
    new_zone_names, _ = build_zone_rows(zones)
    print(f"  Added zones: {new_zone_names}")
    # NameMap adds: zone row names, landmark names referenced, chapter names referenced
    z_adds = list(new_zone_names) + list(new_lm_names) + list(new_chap_names)
    # also primary + addl chapter names (already in chapter names set if newly added)
    for s in STAIRS:
        z_adds.append(s[1])
        for a in s[2]:
            z_adds.append(a)
    nadded_z = add_to_namemap(zones, z_adds)
    print(f"  Zones NameMap +{nadded_z}")
    sync_counters(zones)

    # Phase 3: World.json
    print("\n[Phase 3] Adding StringTable entries...")
    chapter_strings = [(t[5], t[6]) for t in NEW_CHAPTERS]
    all_strings = chapter_strings + new_str_keys
    added = add_stringtable_entries(world, all_strings)
    print(f"  Added {added} stringtable entries")
    # World.json NameMap likely doesn't need updates for new keys (they're values, not FNames)
    # But the keys are typically still in NameMap. Be safe and add them.
    w_adds = [k for k, _ in all_strings]
    w_added = add_to_namemap(world, w_adds)
    print(f"  World NameMap +{w_added}")
    sync_counters(world)

    # Save
    print("\nSaving...")
    save(CHAPTERS_FP, chapters)
    save(LANDMARKS_FP, landmarks)
    save(ZONES_FP, zones)
    save(WORLD_FP, world)
    print("Done.")

if __name__ == "__main__":
    main()
