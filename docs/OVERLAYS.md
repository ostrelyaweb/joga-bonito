# External overlays

Joga Bonito 1.3 implements overlays as separate transparent Windows windows. It
does not inject a DLL, hook the Rocket League renderer, open a local network
port, or bypass anti-cheat.

## Display mode

- **Borderless:** supported and recommended.
- **Windowed:** supported.
- **Exclusive Fullscreen:** not supported because Windows normally places an
  exclusive fullscreen surface above external windows. Select Borderless in
  Rocket League to see the overlays.

## Controls

The **Overlayi / Overlays** page independently enables FPS/frame-time,
controller, keyboard/mouse, session, platform/player, and notification windows.
Each window has its own scale, opacity, and click-through preference.

Use **Edit positions** to temporarily make enabled overlays interactive, then
drag them to the desired locations. Finishing edit mode restores click-through.
Positions are written atomically to `%AppData%\JogaBonito\config\overlays.json`.

`F2` globally hides or shows enabled overlays. If another program owns F2, the
page reports that the hotkey is unavailable and the on-screen button remains
usable. **Show only while the game is running** watches for
`RocketLeague.exe`; it does not attach to or modify that process.

## Data accuracy

Controller state comes from the Windows XInput API. Keyboard/mouse highlights
use read-only Windows key state. Session duration begins when the external game
process is detected. The player panel displays only local installation/platform
information and does not claim an online identity, rank, inventory, or title.

Reliable Rocket League frame timing is not available through the current safe
external providers, so the FPS panel explicitly displays `N/A`. It must not
invent a measurement. A future signed, non-injected provider can feed that panel
without changing the overlay window architecture.
