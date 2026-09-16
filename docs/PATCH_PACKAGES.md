# Joga Bonito patch packages (`.jbpkg`)

Joga Bonito 1.2 uses its own clean-room package format for verified redirect and
paint changes. It does not read Shift `.sbbk` packages and does not inject code
into Rocket League. A package is only applied when the target file's exact size,
SHA-256, and expected bytes all match.

## Container

A `.jbpkg` file is a ZIP archive containing `manifest.json` at its root. Optional
preview images may use PNG, JPEG, or WebP. Scripts, executables, absolute paths,
and parent-directory paths are rejected. The archive is limited to 32 files and
16 MB of uncompressed data.

## Manifest version 1

```json
{
  "format": "joga-bonito.patch",
  "version": 1,
  "id": "example.blue-paint",
  "name": "Example blue paint",
  "author": "Package author",
  "kind": "paint",
  "description": "Changes one verified RGBA value.",
  "target": {
    "file": "Example.upk",
    "size": 123456,
    "sha256": "64-lowercase-hex-characters"
  },
  "operations": [
    {
      "offset": 4096,
      "expected": "ff0000ff",
      "replacement": "0000ffff",
      "label": "Red RGBA to blue RGBA"
    }
  ]
}
```

`kind` is `redirect` or `paint`. Target names must be `.upk` or `.bnk`
basenames. Every operation must preserve byte length, remain inside the file,
and not overlap another operation. Package authors may add
`target.outputSha256` to verify the final patched file as well.

## Application flow

1. Open **Napredne izmjene** and import the `.jbpkg` file.
2. Select the intended Rocket League installation.
3. Run **Provjeri / Dry run**. This does not write to the game directory.
4. Review every listed offset, then apply.
5. Use **Vrati original** to restore the integrity-checked baseline backup.

Joga Bonito refuses the operation if Rocket League has updated the target file,
if expected bytes differ, if a backup was modified, or if the file changed after
the dry run. It also refuses to restore over a newer game update.

## Building manifests safely

`joga_app.patches.builders.build_redirect_patch` creates same-length encoded
reference changes and requires an explicit offset when the old reference occurs
more than once. `build_paint_patch` requires a caller-supplied offset and an exact
RGB/RGBA value at that location. Neither builder guesses offsets.
