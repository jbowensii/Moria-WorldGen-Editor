# Return to Moria — WorldGen Technical Guide

A consolidated reference for everything we have learned about Moria's
procedural world generation while building the editor. Where this guide and
the source code disagree, the source code wins — it is the live truth.

---

## 1. Overview

Return to Moria's procedural world is built from a small set of **DataTables**
(`DT_Moria_Zones`, `DT_Moria_Chapters`, `DT_Moria_Landmarks`,
`DT_Moria_LayoutConnections`, `DT_Moria_Biomes`, `DT_Moria_ZoneDeck`,
`DT_Moria_ZoneBubbleFilters`, `DT_Moria_ZoneTemplates`) and a master
`World` StringTable that holds the human-readable display names.

A "world" is a stack of **chapters** along the Z axis. Each chapter is a
band `[MinZ, MaxZ]` that contains zero or more **zones**. Each zone is a
3D footprint at a `Position` of `TargetSize` cells, optionally pinned to
one or more **landmarks** that act as anchor points. The runtime picks
zone variants from the **ZoneDeck** (the bubble pool per zone) at world-
build time.

The L1 / L2 layout passes run sequentially:

- **L1_PlaceZones** — picks a free spot inside each chapter band for every
  Live zone, honoring overlap and footprint constraints. This is the pass
  that emits "Cannot find empty cell" when a chapter is overstuffed.
- **L2_RouteInterzoneConnections** — runs A* across the parcelized cell
  grid to wire `LayoutConnections` together. This is the pass that null-
  derefs at `FMorLayoutConnectionInstance::GetZone` if NameMap counters
  are stale, or if a chapter has zero Live zones, or if a zone is
  unanchored.

The grid is fixed: **30 x 30 x 30 cells, axes 0..29 inclusive**. Z=30 is
out of bounds and crashes A*. Z=0 is a valid grid cell — only the full
vector `Position=(0,0,0)` is the "generator-placed" sentinel.

---

## 2. DataTable system

Each DataTable is shipped as a UE4.27 `.uasset` + `.uexp` pair. The editor
round-trips them through UAssetGUI's `tojson` / `fromjson` against the
**UAssetAPI JSON** schema (object form: `{"$type":"UAssetAPI.UAsset",
"NameMap":[...], "Imports":[...], "Exports":[...]}`). The FModel JSON
format is not round-trippable and is never used in this pipeline.

### NameMap mechanics

Every FName referenced anywhere in the asset (row keys, struct types,
enum literals, GameplayTag strings, FName-typed properties) MUST be
present in the top-level `NameMap` array. The asset header carries two
additional counters:

- `NamesReferencedFromExportDataCount`
- `Generations[0].NameCount`

Both must equal `len(NameMap)`. If they drift, UE's loader treats trailing
NameMap entries as "out of range" and the L2 routing pass dies on
`FMorLayoutConnectionInstance::GetZone()` with a 0x1a1 read of a null
zone pointer.

The validator's `counter_sync`, `nm_count_mismatch`, `namemap_completeness`,
and `namemap_dups` checks all defend this invariant. The editor calls
`reconcile_namemap()` after every CRUD operation to keep it tight.

### Cross-table references

Many fields reference rows in other DataTables by FName. The
`cross_dt_refs` validator catches dangling references — a zone that
points at a chapter that was renamed, a landmark whose host zone was
deleted, a layout connection whose endpoint disappeared, etc.

---

## 3. Chapter system

Chapters are Z-band buckets. The fields that matter:

| Field | Meaning |
|-------|---------|
| `ZoneSet` | Which campaign mode this chapter belongs to (Moria, SandboxSmall, SandboxMedium, Expedition...) |
| `ChapterID` | Integer used by the in-game map / fast-travel UI; must be unique within the Live SandboxSmall ZoneSet |
| `DisplayName` | StringTable key in `World` — the human-readable floor name |
| `Layer` | Vertical layer index; positive = up from ground, negative = below ground |
| `MinZ` / `MaxZ` / `PrimeZ` | Z band the chapter occupies. `PrimeZ` is the canonical placement Z |
| `EnabledState` | Live / Disabled / etc. Disabled rows are scaffolding; the engine still loads them but skips them |
| `EnemyScalingLevel` | Vanilla caps at 4; new floors should respect that |

`ChapterID` matters for the map UI: duplicate IDs collapse into a single
travel-stone. The validator's `chapterid_duplicates` check enforces
uniqueness within Live SandboxSmall.

`DisplayName` MUST resolve in the `World` StringTable, otherwise the
chapter shows as a missing-key string in-game.
The `chapter_displayname_missing` check enforces this.

---

## 4. Zone system

A zone is a 3D footprint placed inside a chapter band:

- `Chapter` — primary chapter (the "owning" band)
- `AdditionalChapters` — sibling bands a zone can bleed into. Used by
  stairs and elevators that bridge floors.
- `Position` — explicit `(X, Y, Z)` placement. `(0,0,0)` is the
  generator-placed sentinel.
- `TargetSize` — `(X, Y, Z)` cell footprint. Capped at `14 x 14 x 4`.
- `bExtendFootprint` — bubbles below this zone count toward its footprint
  (relevant for tall stairs).
- `bPositionFromLandmarks` — when true, the zone anchors to its
  `LandmarkHandles[]`; otherwise it uses `Position`.
- `LandmarkHandles[]` — list of attached landmark refs, each with optional
  `bExtendedConnectivityLandmark` (= "this is a stair / elevator that
  spans Layer +/- 1").
- `EnabledState` — Live / Disabled.

### The unanchored-zone trifecta

A Live SandboxSmall zone with `bPositionFromLandmarks = true`,
`LandmarkHandles = []`, and `Position = (0,0,0)` has NO anchor. The
runtime null-derefs at `FMorLayoutConnectionInstance::GetZone` 0x1a1.
Easy to introduce when duplicating a zone — the flag copies, the
landmarks do not. Validator: `unanchored_zone` (auto-fix clears the
flag so the generator picks a free cell).

### Stair growth

Stairs and Crystal Descents grow **upward only** from their origin.
The origin is `Position.Z` if pinned, or `LandmarkHandles[].BasePos.Z`
when `bPositionFromLandmarks` is true. The origin sits at the bottom
of the host chapter band (typically `MinZ`). The zone then extends
`Size.Z` cells up, bleeding through chapters above. The top must satisfy
`<= 29`. Stairs never grow downward.

---

## 5. Landmark system

Landmarks are anchor points. Each row carries a `BasePosition (X, Y, Z)`
and a list of host zones (`LandmarkHandles` reverse-resolved). Sentinel
patterns:

- `BasePosition = (0, 0, *)` — sentinel "auto X/Y, fixed Z". Forces the
  generator to pick X/Y but pins Z. Used heavily by vanilla but causes
  XY collisions when multiple stairs share `(0, 0, *)`.
- `BasePosition.Z` MUST be inside the host chapter's `[MinZ, MaxZ]` when
  `bPositionFromLandmarks = true`, otherwise the runtime pins the zone
  outside its band and L2 routing crashes. Re-clamp every landmark Z
  whenever you move a zone between chapters. Validators:
  `landmark_zband_misalign`, `landmark_not_at_minz`, `z_bounds_landmark`.

### Live landmark needs a host

A Live landmark with no host zone is a dangling anchor — the runtime can
reach it via `LandmarkHandles` but the zone is never placed.
Validator: `live_landmark_has_host`.

---

## 6. LayoutConnections

Each LayoutConnection wires two zones together. The runtime A* router
treats them as required edges in the graph. Fields:

- `OriginInterface` / `DestinationInterface` — interface FNames (slot
  identifiers on each zone)
- `OriginZone` / `DestinationZone` — zone FNames
- `bRequired` — A* MUST find a path; an unsatisfiable required edge is a
  crash
- `Subcell.Z` / `PreferredZOverride` — used by extended-connectivity
  stair zones to pin a vertical run

The 14-floor expansion uses 9 explicitly chained `bRequired` zone-to-
zone connections to guarantee A* connects every adjacent stair pair.

### Failure modes

- `connection_null_endpoints` — one of the endpoint FNames doesn't
  resolve. Hot path to a routing crash.
- `connection_endpoint_disabled` — endpoint resolves but the row is
  Disabled. Live -> Disabled refs are the **parcelizer crash class**:
  `MorLayoutParcelizer.cpp:213` reads 0x8 of a null pointer.
- `connection_orphan_endpoint` — endpoint exists but is not in the
  active ZoneSet.

---

## 7. The 14-floor architecture (current state)

The expansion stacks 14 SandboxSmall chapters into the 30-cell Z budget,
sequential vanilla-style 1..14:

| Chapter row | Layer | Floor | ChapterID | MinZ..MaxZ |
|-------------|-------|-------|-----------|------------|
| chapter-1  | 0  | Lv-1 (ground) |  1 | 18..19 |
| chapter-2  | 1  | Lv-2 |  3 | 20..20 |
| chapter-3  | 2  | Lv-3 |  5 | 21..23 |
| chapter-4  | 3  | Lv-4 |  7 | 24..26 |
| chapter-5  | 4  | Lv-5 |  9 | 27..27 |
| chapter-6  | 5  | Lv-6 | 11 | 28..28 |
| chapter-7  | 6  | Lv-7 | 13 | 29..29 |
| chapter-8  | -1 | D-7 (deepest) |  2 | 0..1 |
| chapter-9  | -2 | D-6 |  4 | 2..4 |
| chapter-10 | -3 | D-5 |  6 | 5..8 |
| chapter-11 | -4 | D-4 |  8 | 9..13 |
| chapter-12 | -5 | D-3 | 10 | 14..15 |
| chapter-13 | -6 | D-2 | 12 | 16..16 |
| chapter-14 | -7 | D-1 | 14 | 17..17 |

(Exact bands shift between releases; the table above is the v2.5.3
reference state. The level-list skill prints the live state.)

`ChapterID` follows the odd-up / even-down convention: ground = 1,
upward = 3,5,7,9,11,13, deeps = 2,4,6,8,10,12,14. The story-mode
Moria-* chapters were bumped +100 (101..108) to clear the 1..14 range
so the SandboxSmall map UI doesn't collide with story-mode IDs.

### Stair architecture

Fourteen chapters need a single chain that lets the player walk from
floor 1 to floor 14 (or 14 to 1). Convention as of v2.5.3:

- `FirstStair` .. `FourteenthStair` landmark FNames, one per chapter.
- Odd-numbered stairs anchor at Lv-1..Lv-7 (going up).
- Even-numbered stairs anchor at D-1..D-7 (going down).
- `FirstStair` = Lv-1 (Elevator_B, vanilla preserved).
- Vanilla disabled rows (`SecondStair`..`FifthStair`) are prefixed
  `_disabled_vanilla_` to clear the namespace.

### bRequired chain

Nine zone-to-zone `bRequired` LayoutConnections explicitly chain every
adjacent elevator pair so A* doesn't have to guess:

`TopEl` -> `Lv3Lv4Connector` -> `Elevator_B` -> `D1Lv1Connector` ->
`DeepUpperEl` -> `DeepMidEl` -> `D4D3Connector` -> `DeepBottomEl` ->
`CrystalDescent` -> `D7D6Stair`

### Engine bounds [0..29]

Confirmed empirically:

- `Z=1..30` (14 chapters starting at 1) — **CRASHES** at
  `FMorLayoutConnectionInstance::GetZone()`
- `Z=0..29` (14 chapters using the full budget) — **WORKS**

The bottom chapter MUST start at Z=0 to fit 14 chapters in the budget.

### Embedded-bottom landmarks

`DarkestDeeps`-class landmarks are "embedded bottom" — they need
headroom below them inside the host chapter, so `MinZ < PrimeZ` is
required. Validator: `embedded_bottom_needs_headroom` (ERROR).

---

## 8. Validator rules

The full rule list as of v2.5.3 (from
`scripts/SandboxZoneEditor.py`):

| Rule ID | Class | What it catches |
|---------|-------|-----------------|
| `chapter_stair_uniqueness` | ERROR | A chapter can be primary for at most one stair zone |
| `stair_xy_collision` | ERROR | No two stair landmarks share both X and Y |
| `stair_xy_sentinel_overlap` | WARN | Multiple stairs at `(0, 0, *)` sentinel |
| `embedded_bottom_needs_headroom` | ERROR | DarkestDeeps require host chapter `MinZ < PrimeZ` |
| `z_bounds_chapter` | ERROR | Chapter band outside `[0, 29]` |
| `z_bounds_zone_pos` | ERROR | Zone Position.Z outside `[0, 29]` |
| `z_bounds_zone_top` | WARN/ERROR | Zone top (Position.Z + Size.Z) > 29 |
| `z_bounds_zone_bottom` | ERROR | Zone bottom < 0 |
| `z_bounds_landmark` | ERROR | Landmark BasePosition.Z outside `[0, 29]` |
| `landmark_zband_misalign` | WARN | Landmark Z outside host chapter band |
| `landmark_not_at_minz` | WARN | Anchor landmark not at chapter MinZ (stairs only) |
| `extended_connectivity_no_neighbour` | WARN | Stair landmark with no chapter at Layer +/- 1 |
| `extended_connectivity_z_bounds` | ERROR | Stair span exits world bounds |
| `chapter_layer_continuity` | WARN | Gap in Layer numbering (hides intentional missing floors) |
| `chapter_has_at_least_one_zone` | WARN | Empty Live chapter — map level renders blank |
| `live_landmark_has_host` | WARN | Live landmark not referenced by any host zone |
| `connection_null_endpoints` | ERROR | LayoutConnection endpoint FName doesn't resolve |
| `connection_endpoint_disabled` | ERROR | Live LC -> Disabled zone (parcelizer crash class) |
| `connection_orphan_endpoint` | WARN | Endpoint not in active ZoneSet |
| `namemap_completeness` | ERROR | NameMap missing referenced names |
| `nm_missing_entries` | ERROR | (alias of completeness) |
| `namemap_dups` | WARN | Duplicate names in NameMap |
| `nm_duplicate_entries` | WARN | (alias of dups) |
| `counter_sync` / `nm_count_mismatch` | ERROR | NameMap counters out of sync |
| `unanchored_zone` | ERROR | bPositionFromLandmarks=true with empty handles + (0,0,0) |
| `orphan_added_data` | WARN | AdditionalChapters references a non-existent chapter |
| `chapterid_duplicates` | ERROR | Duplicate ChapterID in Live SandboxSmall |
| `chapter_displayname_missing` | WARN | Chapter DisplayName key not in World StringTable |
| `cross_dt_refs` | ERROR | Cross-table FName reference doesn't resolve |
| `duplicate_rows` | ERROR | Same row name twice in a DataTable |
| `enabled_state` | WARN | EnabledState value isn't a known enum literal |
| `empty_struct_arrays` | WARN | Struct array property has zero entries (UAssetAPI quirk) |
| `live_to_disabled` | ERROR | Live row references a Disabled row |
| `zone_preferred_z_in_band` | WARN | Zone PreferredZOverride outside host band |
| `nested_subcell_z_in_band` | WARN | LC Subcell.Z outside endpoint band |
| `ss_landmark_bp_in_band` | WARN | Sandbox.Small landmark BP outside host band |
| `landmark_pos_lm_loop` | WARN | Landmark referencing itself in Position |
| `stair_bubble_z_oob` | ERROR | Stair bubble Z out of world bounds |

---

## 9. Vanilla-tolerated patterns

Vanilla SandboxSmall ships with several patterns the validator would
flag. The editor has a "vanilla-tolerated" filter (default ON) that
suppresses these:

- `connection_null_endpoints` — vanilla has 4 LCs with null endpoints
- `unanchored_zone` — vanilla has unanchored zones in disabled chapters
- `namemap_completeness` — minor leftover names referenced via guess-FName
- `landmark_zband_misalign` — a couple of landmarks drift outside their
  host band but never get exercised
- `landmark_not_at_minz` — non-stair landmarks anchor mid-band
- `extended_connectivity_no_neighbour` — top/bottom-floor stairs in
  vanilla have a no-op neighbour entry that shows up here

Pristine vanilla audit (153 zone pairs):
- 86% no overlap
- 13 same-chapter full overlaps (the variant pattern)
- 5 same-chapter partial overlaps
- 4 cross-LAYER partial overlaps with max 12% coverage, max 4 cells/axis

Moria campaign vanilla: zero cross-chapter overlap (chapter-isolated).

---

## 10. Common failure modes

### `L2_RouteInterzoneConnections` crash (0x1a1)

`FMorLayoutConnectionInstance::GetZone()` reads 0x1a1 of a null zone
pointer. Causes:

- NameMap counters out of sync (most common)
- Unanchored-zone trifecta (Live SS zone with no anchor)
- Live zone references chapter that's not Live
- Z band overflow (chapter MaxZ > 29 or zone top > 29)

### Parcelizer crash (0x8)

`MorLayoutParcelizer.cpp:213` lambda reads 0x8 of a null. Causes:

- Live LayoutConnection endpoint points at a Disabled zone
- Live zone's `ParentZone` or `SlideToZone` points at a Disabled zone

These are distinct from the routing class — fix one and the other might
become visible.

### "Cannot find empty cell"

L1 placement gave up. The chapter band is too small for the zone count
trying to fit, OR a zone's `TargetSize` exceeds the band height, OR
overlap rules can't be satisfied. Check chapter Z-budget vs zone size
sum, and remember the `<= 4 cells per axis` cross-chapter limit.

### Map missing levels

Empty chapter — no Live zones in the band. The map UI buckets per
chapter, so an empty band renders as a blank floor. Validator:
`chapter_has_at_least_one_zone`.

### Stair routing failures

Two stair landmarks share XY, or a stair anchors at a sentinel
`(0, 0, *)` and the generator picks the same XY for two of them.
Validators: `stair_xy_collision`, `stair_xy_sentinel_overlap`.

### Bisection-by-disable

When stuck on a routing/parcel crash, set EnabledState=Disabled on
suspect zones (NOT chapters — keep chapter rows Live for scaffolding)
and clear any Live-zone-to-now-Disabled refs to None. Re-enable in
groups to localize.

---

## 11. Build pipeline

The editor's build pipeline is the proven IoStore round-trip:

```
DT_Moria_*.json
  -> UAssetGUI fromjson VER_UE4_27
  -> staging/Moria/Content/Tech/Data/GameWorld/DT_Moria_*.uasset + .uexp
  -> retoc to-zen --version UE4_27
  -> WorldGenMod_P.pak / .ucas / .utoc
  -> zip to ~/Downloads/WorldGenMod_v{VERSION}.zip
```

Version-string gotcha:

| Tool | Flag |
|------|------|
| UAssetGUI | `VER_UE4_27` (with VER_ prefix, underscore) |
| retoc     | `UE4_27` (NO VER_ prefix) |

**NEVER use `--override-container-header-version`** with retoc. It
corrupts the container header and produces an `EXCEPTION_ACCESS_VIOLATION`
at game launch.

The `DATATABLES` registry at the top of `SandboxZoneEditor.py`
determines which DTs the build pipeline bundles. If a DT has a modified
`.json` and a `.original.json` sidecar but isn't registered, the build
SILENTLY ships the pristine uasset — producing an inconsistent pak that
crashes A* every time. Always include `DT_Moria_LayoutConnections` and
`DT_Moria_ZoneTemplates` in the registry alongside the obvious ones.

---

## 12. Project rules / invariants

- **Z bounds**: every chapter `MinZ >= 0`, every chapter `MaxZ <= 29`,
  every zone top `<= 29`.
- **World X/Y bounds**: 0..29 inclusive.
- **TargetSize cap**: `14 x 14 x 4`.
- **Same-chapter overlap**: 0% to 100% allowed (variant pattern).
- **Cross-chapter overlap**: <= 20% coverage on either zone.
- **Single-axis overlap**: <= 4 cells.
- **Chapter Z budget**: sum of heights <= 30.
- **`Position=(0,0,0)`** is the generator-placed sentinel; `Z=0` alone
  is a valid grid cell.
- **Zone shrink budget**: up to 20% per zone, used to resolve overlap
  violations.
- **Landmark BasePosition.Z** must be inside host chapter `[MinZ, MaxZ]`
  whenever `bPositionFromLandmarks=true`. Re-clamp on every move.
- **Extended-connectivity stairs** require Live chapters at both
  Layer+1 AND Layer-1. Top/bottom edges crash unless special-cased.
- **ChapterID uniqueness** within Live SandboxSmall. Story-mode chapter
  IDs sit in the 100s to clear the SS range.
- **Chapter DisplayName** must reference a key in the `World`
  StringTable.
- **DATATABLES registry** must include every modified DT JSON.
- **Stairs grow upward only** from origin in host chapter band; top
  must satisfy `<= 29`.

These invariants are why the validator exists.
