# Release Notes

## v2.5.3 — 2026-04-30

Chapter rename + stair conventions + cleanup. World loads in-game and the
validator is clean, but floor / map generation has visual issues to address
in the next iteration.

- Chapter renumber to vanilla-style sequential 1..14:
  - `chapter-1`..`chapter-7` = Lv-1..Lv-7 (going up from ground; ChapterID
    matches floor number)
  - `chapter-8`..`chapter-14` = D-7..D-1 (deeps; chapter-8 = D-7,
    chapter-14 = D-1)
  - 10 chapter rows renamed via temp-prefix swap to avoid collisions
  - 56 zone references updated (34 `Chapter` + 22 `AdditionalChapters`)
  - DisplayName updated per chapter to match the correct floor StringTable key
- `EnemyScalingLevel` aligned to vanilla 0..4 cap:
  - Lv-1=0, Lv-2=1, Lv-3=2, Lv-4=3 (vanilla unchanged)
  - Lv-5/Lv-6/Lv-7 = 4 (capped at vanilla max)
  - D-1=1, D-2=2, D-3=3, D-4=4 (vanilla unchanged)
  - D-5/D-6/D-7 = 4 (capped at vanilla max)
- Stair landmarks renamed to the
  `FirstStair`..`FourteenthStair` convention:
  - Odd-numbered stairs anchor at Lv-1..Lv-7 (going up)
  - Even-numbered stairs anchor at D-1..D-7 (going down)
  - 1st = Lv-1 (Elevator_B, vanilla preserved)
  - 5th = Lv-3 (was Lv3Lv4Connector), 7th = Lv-4 (was TopElevator)
  - 2nd = D-1, 4th = D-2, 6th = D-3, 8th = D-4, 10th = D-5, 12th = D-6,
    14th = D-7
  - Vanilla disabled rows (`SecondStair`..`FifthStair`) prefixed
    `_disabled_vanilla_` to clear the namespace
  - `Chapter1.ElvenQuarterEntrance` landmark prefix renamed (was Chapter2)
- NameMap orphan cleanup (conservative — UE built-in type whitelist
  preserved):
  - `DT_Moria_Zones.json`: 1228 -> 1201 (27 stale strings removed)
  - `DT_Moria_Landmarks.json`: 311 -> 279 (32 stale)
  - `DT_Moria_LayoutConnections.json`: 287 -> 274 (13 stale)
  - `DT_Moria_Chapters.json`: 75 (no change — all referenced)
  - All counters synced across NameMap /
    `NamesReferencedFromExportDataCount` / `Generations[0].NameCount`
- Z=30 OOB fix (compressed top stack):
  - chapter-4 MaxZ shrunk to a 3-cell band (24..26)
  - chapter-9/10/11 (now chapter-5/6/7) shifted down by 1
  - DestroyedCity_A / Gundabad / Dwarrowdelf Position.Z shifted, landmarks
    followed
  - `Sandbox.MithrilMineNexus` BP.Z 0 -> 4 to follow AngryCaverns_B move
- Editor: "Hide Layer 0" filter renamed to **"Hide unassigned zones"**
  (correct semantics — filters by ZoneSet=SandboxSmall + EnabledState=Live,
  not Layer=0)

Validator state at v2.5.3: 0 errors, 25 warnings (all pre-existing
vanilla noise). Deep verify: 11/11 pass.

Known issue: `Sandbox_Small_DestroyedCity_A_Desolation` has TargetSize.Z=7
with PreferredZOverride=29, producing a footprint Z=29..35 that overflows
the engine ceiling Z=29 by 6 cells. Validator flags via `z_bounds_zone_top`
warning. World loads but Lv-7 area is mis-rendered.

---

## v2.5.2 — 2026-04-30

Full 14-floor elevator chain + ChapterID renumber + Zones-tab UX.
Comprehensive worldgen restructure plus editor UX improvements layered on
top of v2.5.1.

Worldgen architecture:

- Built the full 14-floor elevator chain spanning D-7 through Lv-7 with 9
  elevator/stair zones. Every chapter has exactly one stair START anchored
  as primary, with 1-floor overlaps between adjacent zones. Mix of
  Size.Z=4 (most) and Size.Z=5 (DeepUpperEl, DeepBottomEl) bridges.
- 9 zone-to-zone `bRequired` LayoutConnections explicitly chain every
  adjacent elevator pair (TopEl -> Lv3Lv4Connector -> Elevator_B ->
  D1Lv1Connector -> DeepUpperEl -> DeepMidEl -> D4D3Connector ->
  DeepBottomEl -> CrystalDescent -> D7D6Stair) — guarantees A* connects
  every floor.
- Disabled vanilla Elevator_C/D/E/F (replaced by the new chain) and their
  orphan landmarks (`Sandbox.SecondStair`..`FifthStair`). Mines_C kept
  Live but `bExtendedConnectivityLandmark` flag cleared (it was a
  chapter-boundary mine landmark, not a real elevator).
- Chapter band expansions on 5 chapters (MinZ pulled down into landmark-
  reserved cells): Lv-2 (19..20), D-1 (14..17), D-2 (10..13),
  D-4 (5..8), D-5 (2..4). PrimeZ unchanged.
- 9 new stair landmarks with explicit non-zero X/Y to eliminate sentinel
  collisions.
- `Chapter3.CrystalDescent` landmark relocated from chap-3 to D-7 anchor
  (16, 14, 0).

Map / fast-travel ChapterID renumber (odd-up / even-down convention from
ground):

- Lv-1 ground = ChapterID 1
- Lv-2..Lv-7 = ChapterID 3, 5, 7, 9, 11, 13 (odd, up)
- D-1..D-7 = ChapterID 2, 4, 6, 8, 10, 12, 14 (even, down)
- 8 SandboxMedium chapters disabled (had duplicate IDs 1-8 + held the
  DisplayName keys we needed)
- 7 Moria-* + Expedition story-mode chapters bumped +100 (now 101..108) to
  clear the 1..14 range

Editor UX:

- Zones tab: drag-and-drop replaced by right-click **"Move to chapter…"**
  context menu (more reliable; off-screen chapters reachable via picker
  dialog with full chapter list)
- Zones tab: new **"Hide Layer 0"** checkbox filters out zones whose
  primary chapter is Layer=0
- Chapter-grouped Treeview retained from v2.5.1
- New `ZoneMover` / `ZoneMoveDialog` / `ZoneMoveResultDialog` classes
  back the move pipeline: snapshot -> preflight (Z-bleed /
  AdditionalChapters drift detection) -> conflict resolution -> apply
  (chapter rename, Position.Z, landmark BPs, AdditionalChapters, nested
  Subcell.Z, PreferredZOverride) -> validate -> result popup with rollback
  button

BuildValidator extensions:

- `chapter_stair_uniqueness` (ERROR): each chapter must be primary for
  at most one stair zone
- `stair_xy_collision` (ERROR): no two stair landmarks share both X and Y
- `stair_xy_sentinel_overlap` (WARN): flags landmarks at `(0, 0, *)`
  sentinels
- `embedded_bottom_needs_headroom` (ERROR): DarkestDeeps require host
  chapter `MinZ < PrimeZ`

State at v2.5.2: 0 validator errors, 24 warnings. Deep verify: 11/11
pass. Cross-reference audits: 10/10 pass. All 4 NameMap counters synced.

---

## v2.5.1 — 2026-04-29

14-floor Z-shift + 5-stair architecture + Lv-4 fix. Milestone where all 8
vanilla SandboxSmall levels render on the in-game map (Lv-1..Lv-4,
D-1..D-4) on a Z layout pre-expanded to support up to 14 levels. Lv-5..7
+ D-5..7 chapters present in data but not yet visible on the map (suspected
hardcoded engine UI cap on Layer range -4..+3 — separate investigation).

- Vanilla SandboxSmall shifted +7 cells (Lv-1 MinZ now 18) preserving
  relative geometry. All 75 Z-bearing fields updated including nested
  LayoutConnection Subcell.Z and PreferredZOverride.
- 6 new chapter rows added (chapter-9..14) for Lv-5/6/7 + D-5/6/7 with
  proper StringTable display names ("The Fifth Level" through "The
  Seventh Deep").
- 5-short-stair architecture replaces the over-aggressive 8-stair build
  that was crushing neighbor-floor content via TS.Z=4 +
  bExtendFootprint=true bubbles. TopStair, UpperStair, GroundStair,
  MidDeepStair, BottomStair — Size.Z=1 or 2, bExtendFootprint=false,
  AdditionalChapters lists 2-3 sibling floors per stair.
- Chapter-4 (Lv-4) expanded to 4-cell band Z=22..25 to fit 4-tall zones
  (DestroyedCity_B, DarkestDeeps_E, AngryCaverns_C). Chapter-9 (Lv-5)
  shifted up to Z=26 to maintain non-overlap.
- 4 ch-4 unanchored zones reverted to vanilla auto-place pattern after
  expansion.
- BuildValidator extended with 4 new checks: `stair_bubble_z_oob`,
  `chapter_layer_continuity`, `chapter_has_at_least_one_zone`,
  `live_landmark_has_host`. Added vanilla-tolerated filter (default ON)
  covering 6 check IDs that vanilla ships with:
  `connection_null_endpoints`, `unanchored_zone`,
  `namemap_completeness`, `landmark_zband_misalign`,
  `landmark_not_at_minz`, `extended_connectivity_no_neighbour`.
- All 4 NameMap counters synced (`NameMap len ==
  NamesReferencedFromExportDataCount == Generations[0].NameCount`)
  across Zones, Chapters, Landmarks, LayoutConnections.

Validator state at v2.5.1: 0 errors, 23 warnings. Deep verify: 11/11
pass. Backup at
`experiments/worldgen_research/backups/8 levels working - 14 level space/`.

---

## v2.5.0 — 2026-04-26

Row CRUD on every data tab + humanized validator UX.

1. **Uniform Add / Copy / Delete row CRUD on every data-row tab** (~430
   LOC). StringsTab, ZoneTab, ChapterTab, BiomeTab, BubbleTab, FilterTab,
   LandmarkTab, and LayoutConnectionsTab all now have a consistent
   "Add row… / Copy row… / Delete row" trio. Copy deep-copies the
   selected row, prompts for a new RowName (default `<src>_copy`),
   reconciles NameMap, refreshes the tab, and marks the doc dirty. Add
   prompts for a fresh name; Delete uses an `askyesno` confirmation.
   Latent-bug fix: `ChapterTab._append_chapter` now calls
   `reconcile_namemap()` to match every other path.

2. **Humanized pre-build validator dialog** (~483 LOC). Replaces the dense
   yes/no messagebox with a 760x540 modal Toplevel.
   - All 20+ check IDs translated to plain-English titles. No more
     `[extended_connectivity_no_neighbour]` jargon shown to the user.
   - Each issue rendered with a bold title, 1-2 line explanation, and
     muted technical detail underneath.
   - Per-issue auto-fix checkboxes (errors pre-checked, warnings
     unchecked).
   - "Apply selected auto-fixes" runs every checked fixer, saves dirty
     docs, re-validates, and refreshes the dialog in place. When all
     issues clear, a green "All clear" banner replaces the list and the
     action button retitles to "Build now".
   - Legacy messagebox flow preserved behind `USE_NEW_VALIDATOR_UI`
     feature flag for fallback.

---

## v2.0.0 — 2026-04-26

14-chapter SandboxSmall expansion + validation pipeline. Major release of
the SandboxZoneEditor tool for editing Return to Moria worldgen
DataTables with safe round-trip through UAssetGUI fromjson + retoc to-zen.

- 16 BuildValidator checks covering NameMap, Z-bounds, unanchored zones,
  landmark MinZ alignment, extended-connectivity stair neighbours,
  ChapterID uniqueness, Live-zone-to-Disabled-target refs, parcelizer
  crash class (Live LayoutConnection -> Disabled zone endpoints), etc.
- Iterative NameMap completeness walk (50 ms vs the prior recursive walk
  that took minutes against a 7 MB DT_Moria_Zones).
- Build pipeline correctly registers `DT_Moria_LayoutConnections` and
  `DT_Moria_ZoneTemplates` so all 9 modified DataTables ship together.
- Locked-in worldgen rules documented in `docs/` (Worldgen Rules and
  Constraints, Bisection Plan, crash analyses).
- Companion scripts in `scripts/` generate worldgen architecture docs.
