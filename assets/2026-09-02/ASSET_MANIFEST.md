# Design Direction Asset Manifest — 2026-09-02

This manifest accompanies `DESIGN_DIRECTION_CHANGE_2026-09-02.md`.

## Generated inspection renders

| Repo path | SHA-256 | Meaning |
|---|---|---|
| `assets/2026-09-02/Ferrari_488_GTE_full_VTK.png` | `ae2d7228a7de4acd22f0b5aced2102c7b96e8b7c08922437faf26b6e3da2d2f6` | Full-scene VTK inspection render |
| `assets/2026-09-02/Ferrari_488_GTE_rear_cutaway_top.png` | `3134ad02adb17900c3add2056b8015e795d90109f936079f70f5b723eab758bd` | Top/rear cutaway inspection view |
| `assets/2026-09-02/Ferrari_488_GTE_rear_cutaway_iso.png` | `ff79772f0c6d3b48e183cb6201f48c2ba8e377875a74bdae318b601b25c0c6be` | Rear isometric cutaway inspection view |

## Project-authored lightweight 3D proxies

| Repo path | SHA-256 | Meaning |
|---|---|---|
| `assets/2026-09-02/f488_gte_1_18_outer_envelope_proxy.glb` | `6a99c8bc5f32edb44844dd867eec67a8778425ad5a380c504435608c5cb822a9` | Simple ~262.8 x 121.4 x 66.1 mm 1:18 outer bounding envelope + axes. **Not the Ferrari surface mesh.** |
| `assets/2026-09-02/v8_8p5x5_packaging_seed.glb` | `acc9e21860baa9b1d399f3a84b11b1c7c19d0cdb2420e3b87c29410706ba72b0` | Conceptual 90-degree V8 packaging seed. **Not engineering CAD.** |

## Third-party/local source mesh archive

The detailed source archive used for inspection is intentionally not included in the public repository because redistribution/license status was not established and the file is large (~68 MB).

Local filename used during the study:

`unpacked-ferrari-488-gte.zip`

SHA-256:

`da74787efbc804fa706248858f170e9c291d7c2e0348e19a9a70f39e045ee6a4`

If a later agent needs exact source-mesh geometry, reacquire/request the archive and verify provenance/hash rather than treating the proxy GLB as the source model.