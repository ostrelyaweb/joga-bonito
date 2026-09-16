# Workshop packages (`.jbworkshop`)

A `.jbworkshop` file is a ZIP container with a root `manifest.json`, optional
root preview images, and declared game files under `payload/`. Packages support
`maps`, `balls`, `decals`, and `hud` categories. No content is bundled with Joga
Bonito; users import only content they are permitted to use.

Each manifest uses `format: joga-bonito.workshop`, `version: 1`, package identity
fields, and 1–64 file records. A record supplies `source`, target basename,
`add` or `replace` mode, payload size, and SHA-256. Replace records must also
provide the exact original target size and SHA-256. Supported payloads are
`.upk`, `.tfc`, and `.bnk` only.

Import verifies the archive path, declared file set, sizes, and hashes before
extracting into `%AppData%\JogaBonito\workshop`. Installation is refused while
Rocket League is running. Every change is journaled; replacements receive an
integrity-checked backup, additions are tracked for safe removal, and any
failure rolls back the entire package. Restore is refused if an installed file
or backup changed afterward, preventing an older package from overwriting a
newer game update.

Executables, scripts, undeclared files, absolute paths, parent traversal,
duplicate targets, unsupported extensions, and payloads over 1 GB are rejected.
