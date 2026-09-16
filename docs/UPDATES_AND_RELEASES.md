# Signed updates and Windows releases

Joga Bonito 1.5 checks an HTTPS release channel without trusting HTTPS alone.
`releases/stable.json` is an Ed25519-signed envelope. The public key is embedded
in the application; the private release key is never committed. Both manifest
signature and downloaded package size/SHA-256 must match before an installer is
offered to the user. Downloads are staged below
`%AppData%\JogaBonito\updates` and are never launched automatically.

The release private key generated for this project is stored outside the Git
repository at `C:\Users\Korisnik\Downloads\JogaBonito-release-key-2026.pem`.
Keep it private and backed up securely. Losing it requires shipping a new app
version with a new embedded public key; exposing it requires immediate rotation.

## Build

Install build dependencies with `python -m pip install -r requirements-build.txt`.
Run `build_release.ps1` to execute all tests, build the standalone PyInstaller
folder, create a portable ZIP, and compile the per-user Inno Setup installer
when Inno Setup 6 is installed. Python and Shift are not required on the target
computer.

To produce `releases/stable.json`, pass the private key and final HTTPS download
URL to the build script. Upload the exact generated installer/ZIP to that URL,
then publish the signed JSON at the configured stable-channel URL. Never edit a
signed field by hand after signing.

## Windows runtime compatibility

The release script isolates PyInstaller from the launching shell's `PATH` and
rejects external ICU DLLs. This prevents `WinError 127` / `DLL load failed while
importing QtGui` when unrelated developer or media tools expose an incompatible
`icuuc.dll` that PyInstaller would otherwise silently embed in the application.
The installer also removes ICU DLLs left behind by version 1.5.0 during an
in-place upgrade, so an existing broken installation is repaired automatically.
