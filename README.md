# Moria WorldGen Editor

Tkinter GUI for editing Return to Moria SandboxSmall worldgen DataTables.

**Status:** v2.5.3 | Python 3.9+ | UE4.27 IoStore mod pipeline

## What it does

The Moria WorldGen Editor is a desktop tool for safely round-tripping the
Return to Moria worldgen DataTables (`DT_Moria_Zones`, `DT_Moria_Chapters`,
`DT_Moria_Landmarks`, `DT_Moria_LayoutConnections`, `DT_Moria_Biomes`,
`DT_Moria_ZoneDeck`, `DT_Moria_ZoneBubbleFilters`, `DT_Moria_ZoneTemplates`,
and the `World` StringTable) through UAssetGUI's `tojson` / `fromjson`
conversion and packaging the result into an IoStore mod pak via `retoc`.

It exposes one tab per DataTable, with row CRUD, a built-in `BuildValidator`
that catches more than two dozen distinct crash classes before you ever launch
the game, and a one-click build pipeline that produces a working `_P.pak` /
`.ucas` / `.utoc` triplet ready to drop into `Content/Paks/`.

The editor focuses on the SandboxSmall ZoneSet — the only sandbox mode in
Moria with actual zone definitions. It is the main editing surface used to
build the 14-floor expansion (Lv-1..Lv-7 going up, D-1..D-7 going down) on
top of the vanilla 8-chapter game, including the full elevator/stair chain
that ties them all together.

## Features

- **Per-tab DataTable row CRUD** — Add, Copy, Delete on every data-row tab
  (Zones, Chapters, Landmarks, Biomes, BubbleFilters, ZoneDeck,
  LayoutConnections, ZoneTemplates, Strings)
- **BuildValidator** with 30+ checks:
  `chapter_stair_uniqueness`, `stair_xy_collision`,
  `stair_xy_sentinel_overlap`, `embedded_bottom_needs_headroom`,
  `z_bounds_chapter`, `z_bounds_zone_pos`, `z_bounds_zone_top`,
  `z_bounds_zone_bottom`, `z_bounds_landmark`, `landmark_zband_misalign`,
  `landmark_not_at_minz`, `extended_connectivity_no_neighbour`,
  `extended_connectivity_z_bounds`, `chapter_layer_continuity`,
  `chapter_has_at_least_one_zone`, `live_landmark_has_host`,
  `connection_null_endpoints`, `connection_endpoint_disabled`,
  `connection_orphan_endpoint`, `namemap_completeness`, `namemap_dups`,
  `counter_sync`, `unanchored_zone`, `orphan_added_data`,
  `chapterid_duplicates`, `chapter_displayname_missing`,
  `cross_dt_refs`, `duplicate_rows`, `enabled_state`,
  `empty_struct_arrays`, `live_to_disabled`,
  `zone_preferred_z_in_band`, `nested_subcell_z_in_band`,
  `ss_landmark_bp_in_band`, `landmark_pos_lm_loop`,
  `stair_bubble_z_oob`
- **Humanized validator UI** — plain-English titles, per-issue auto-fix
  checkboxes, "Apply selected fixes" + re-validate flow
- **"Hide unassigned zones" filter** — surface only Live SandboxSmall zones
- **Right-click "Move to chapter…"** with snapshot, conflict resolution
  dialog, and rollback
- **NameMap auto-sync** — keeps `NameMap`, `NamesReferencedFromExportDataCount`
  and `Generations[0].NameCount` aligned (mismatch is the
  `L2_RouteInterzoneConnections` crash class)
- **Pak build pipeline** — UAssetGUI `fromjson` (VER_UE4_27) then retoc
  `to-zen` (UE4_27); produces a deployable `_P` triplet, optionally
  zipped to `~/Downloads/`
- **Map view** — true-position 3D overlay with chapter filtering, label
  toggles, drag-to-pan, and connection rendering

## Requirements

- **Python 3.9+** (Tkinter is bundled with the official python.org
  installers)
- **UAssetGUI** v1.0.2+ — for tojson / fromjson
- **retoc** v0.1.5+ — for IoStore packaging
- **Return to Moria** (UE4.27 IoStore mod pipeline)

## Setup

```
git clone https://github.com/jbowensii/Moria-WorldGen-Editor.git
cd Moria-WorldGen-Editor
```

Edit `scripts/SandboxZoneEditor.ini` and set the four paths in `[paths]`:

```
game_path      = C:\Program Files\Epic Games\ReturnToMoria
uassetgui_path = C:\Tools\UAssetGUI\UAssetGUI.exe
retoc_path     = C:\Tools\retoc\bin\retoc.exe
working_dir    = C:\Tools\MoriaWorking
```

The `working_dir` is where the editor expects to find the decompiled
DataTable JSONs (e.g. `DT_Moria_Zones.json`). Generate them once with
UAssetGUI:

```
UAssetGUI.exe tojson "<game>\Moria\Content\Tech\Data\GameWorld\DT_Moria_Zones.uasset" "<working_dir>\DT_Moria_Zones.json" VER_UE4_27
```

Repeat for `DT_Moria_Chapters`, `DT_Moria_Landmarks`,
`DT_Moria_LayoutConnections`, `DT_Moria_Biomes`, `DT_Moria_ZoneDeck`,
`DT_Moria_ZoneBubbleFilters`, `DT_Moria_ZoneTemplates`, and `World`
(the StringTable).

Then launch the editor:

```
python scripts/SandboxZoneEditor.py
```

## Quick start

1. **Load** — File -> Open working dir, or just launch (it auto-loads from
   `working_dir`).
2. **Edit** on the per-DataTable tabs. Modified rows highlight; the doc is
   marked dirty.
3. **Validate** — Build -> Run validator. Apply auto-fixes, re-run, repeat
   until "All clear".
4. **Build pak** — Build -> Build pak. The editor writes `_P.pak` /
   `.ucas` / `.utoc` to your downloads folder, optionally zipped.
5. **Deploy** — drop the triplet into
   `<game>\Moria\Content\Paks\WorldGenMod\` and launch the game.

## License

MIT — see [LICENSE](LICENSE).

## Author

[jbowensii](https://github.com/jbowensii)

## Related projects

- **Moria-Replication** — parent project that owns the legacy-asset
  pipeline, decompiled DataTables, and broader RtM modding toolchain.
- **CleanSweep** — companion mod that uses the same IoStore pipeline to
  remove world-generated objects.

## Documentation

- [WORLDGEN_GUIDE.md](WORLDGEN_GUIDE.md) — comprehensive technical guide
  to the Moria worldgen system, the 14-floor architecture, validator
  rules, and crash classes.
- [RELEASE_NOTES.md](RELEASE_NOTES.md) — version history.
