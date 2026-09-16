# Joga Bonito Production Expansion Design

Date: 2026-09-16

## Objective

Expand Joga Bonito into a standalone, production-grade Rocket League companion application. The implementation is clean-room: it does not copy Shift source code, binaries, licensed assets, protocols, or private services, and it does not depend on Shift at runtime.

The product may provide legitimate local customization, overlays, session information, package management, updates, and distribution. It will not provide identity spoofing, inventory or title falsification, ping spoofing, anti-cheat bypasses, process injection, or features intended to misrepresent account state.

## Delivery phases

### Phase 1: foundation and data safety

- Move mutable user data to `%AppData%\JogaBonito`.
- Migrate existing settings, presets, swap history, signatures, and backups without data loss.
- Assign each configured Rocket League installation a stable internal identifier.
- Introduce atomic JSON storage, structured logging, transaction journals, integrity hashes, and automatic recovery.
- Preserve compatibility with existing Joga Bonito presets and swap history.

### Phase 2: advanced item changer

- Retain ordinary package swaps and companion texture/sound handling.
- Add an independently designed redirect-rule format.
- Add paint variants with validation and previews.
- Add change plans, preflight checks, backup verification, rollback, restore-all, and drift recovery.
- Use a documented Joga package and backup format rather than Shift's `.sbbk` format.

### Phase 3: safe external overlays

- Add FPS/frame-time, controller, keyboard/mouse, session tracker, platform/player display, and notification overlays.
- Implement overlays as transparent always-on-top Windows windows; do not inject into Rocket League.
- Support Borderless/Windowed play. Exclusive Fullscreen is not supported.
- Let users enable or disable every overlay independently from a new Overlays page.
- Support per-overlay position, scale, opacity, click-through state, edit mode, auto-show while the game runs, and reset.
- Add a configurable global show/hide hotkey, defaulting to `F2`.

### Phase 4: workshop and packages

- Add local libraries for workshop maps, ball packs, decal packs, and HUD packs.
- Support import, manifest validation, preview, installation, backup, restoration, and removal.
- Reject executables, scripts, absolute paths, directory traversal, and unsupported file types in imported packages.
- Do not redistribute third-party protected content.

### Phase 5: update and distribution

- Add update checks against a Joga-controlled signed manifest.
- Verify both package hashes and manifest signatures before applying an update.
- Produce a portable Windows build and a Windows installer that bundle Python, Qt, and required libraries.
- Verify operation on a clean Windows user profile without Python or Shift installed.

## Architecture

The existing Python and PySide6 foundation remains. Responsibilities are separated into testable packages:

```text
joga_app/
  core/       configuration, paths, migrations, events, logs, transactions
  swaps/      plans, ordinary swaps, redirect rules, paint, backup, rollback
  overlays/   manager, base window, FPS, controller, KBM, tracker, platform
  workshop/   catalog, package manifests, import, install, restore
  update/     manifests, signature checks, download staging, handoff
  ui/         pages and dialogs that call services but do not alter files directly
```

UI code never directly edits Rocket League files. It requests an operation from a service and renders progress or errors delivered through Qt signals. A central event bus connects long-running services to the UI without introducing a network listener.

## User data layout

```text
%AppData%\JogaBonito\
  config\settings.json
  config\overlays.json
  data\presets.json
  data\history.json
  transactions\
  backups\<installation-id>\
  packages\balls\
  packages\decals\
  packages\hud\
  workshop\
  logs\
```

Program assets remain read-only beside the application. Mutable state is written atomically by writing and validating a temporary file before replacing the previous document.

## Swap transaction model

Every mutation follows the same sequence:

1. Resolve and validate the configured installation.
2. Ensure every target stays within the expected Rocket League directory.
3. Validate source files, package type, compatibility, and free disk space.
4. Create a transaction journal containing format version, operation type, paths, hashes, and planned actions.
5. Create and verify backups.
6. Produce changes in temporary files.
7. Validate output signatures and expected sizes.
8. Atomically replace targets.
9. Mark the journal committed and update preset/history state.

On failure, completed steps are reversed. On startup, incomplete journals are detected and safely rolled back or presented for recovery.

## Overlay model

`OverlayManager` owns independent overlay windows derived from a shared base class. Each window is frameless, transparent, always on top, and click-through outside edit mode. Overlay state is stored in `overlays.json` and restored at startup.

The manager detects whether Rocket League is running and may automatically show configured overlays. Data reaches overlays through local Qt signals. No local server or open port is required. FPS readings must use a safe external measurement mechanism; if reliable frame timing is unavailable, the UI must show an explicit unavailable state rather than invent values.

## Error handling and security

- Never modify a file without a verified backup.
- Prevent path traversal and writes outside configured roots.
- Refuse unsafe package contents and malformed manifests.
- Avoid modifying game files while they are locked or actively in use.
- Keep logs free of license keys, tokens, full account identifiers, and unnecessary personal data.
- Use explicit actionable errors and preserve recovery information.
- Do not inject code, bypass anti-cheat, falsify inventory/rank/title state, or manipulate network latency.

## Testing strategy

- Unit tests cover configuration, migrations, atomic JSON, hashing, manifests, redirect rules, and paint data.
- Transaction tests inject failures after every mutation step and verify complete rollback.
- UI tests cover enable/disable, positioning, scaling, opacity, edit mode, click-through, persistence, and hotkeys.
- Integration tests use a synthetic `CookedPCConsole` fixture, never a real game installation.
- Packaging smoke tests run the portable build and installer output on a clean profile without Python or Shift.
- A real installation is tested only after automated tests pass and initially only against a controlled copy of a game file.

## Acceptance criteria

- Existing Joga settings, swaps, presets, and backups survive migration.
- The application starts and operates without Shift or system Python.
- Every overlay can be independently enabled and disabled in Joga Bonito.
- A failed file operation leaves the game installation byte-for-byte recoverable.
- Package imports cannot escape their managed directories or execute code.
- Automated tests cover the safety-critical transaction and migration paths.

