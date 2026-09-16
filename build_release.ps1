param(
    [string]$PrivateKey = "",
    [string]$PackageUrl = "",
    [string]$BuildRoot = "",
    [string]$OutputDir = "",
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not $BuildRoot) {
    $BuildRoot = $PSScriptRoot
}
if (-not $OutputDir) {
    $OutputDir = Join-Path $PSScriptRoot "release-output"
}
$buildDir = Join-Path $BuildRoot "build"
$distDir = Join-Path $BuildRoot "dist"
$appDist = Join-Path $distDir "JogaBonito"

& $PythonExe -m unittest discover -s tests -v

# Dependency resolution must not inherit DLL directories from the shell that
# launched this build (for example Codex, Git, media tools, or another Qt app).
# PyInstaller otherwise resolves generic names such as icuuc.dll from those
# directories and silently embeds an ABI-incompatible third-party copy.
$resolvedPython = (Get-Command $PythonExe -ErrorAction Stop).Source
$originalPath = $env:PATH
try {
    $env:PATH = "$env:WINDIR\System32;$env:WINDIR"
    & $resolvedPython -m PyInstaller --clean --noconfirm --workpath $buildDir --distpath $distDir JogaBonito.spec
} finally {
    $env:PATH = $originalPath
}

$contaminatedIcu = @(Get-ChildItem -LiteralPath (Join-Path $appDist "_internal") -File -ErrorAction Stop |
    Where-Object { $_.Name -match '^icu(?:uc|dt\d*)\.dll$' })
if ($contaminatedIcu.Count -gt 0) {
    throw "Build contains unexpected external ICU DLLs: $($contaminatedIcu.Name -join ', ')"
}
Write-Output "Verified clean Windows DLL dependency set."

$releaseDir = $OutputDir
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
$portable = Join-Path $releaseDir "JogaBonito-Portable-1.5.1.zip"
if (Test-Path -LiteralPath $portable) { Remove-Item -LiteralPath $portable -Force }
Compress-Archive -LiteralPath $appDist -DestinationPath $portable -CompressionLevel Optimal

$isccCandidates = @(@(
    (Get-Command iscc -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) })
if ($isccCandidates.Count -gt 0) {
    & $isccCandidates[0] "/DSourceDir=$appDist" "/DReleaseDir=$releaseDir" (Join-Path $PSScriptRoot "installer\JogaBonito.iss")
} else {
    Write-Warning "Inno Setup not found; portable build was created, installer was skipped."
}

if ($PrivateKey -and $PackageUrl) {
    $installer = Join-Path $releaseDir "JogaBonito-Setup-1.5.1.exe"
    $package = if (Test-Path -LiteralPath $installer) { $installer } else { $portable }
    $kind = if ($package.EndsWith(".exe")) { "installer" } else { "portable" }
    & $PythonExe tools\sign_release.py --package $package --url $PackageUrl --version 1.5.1 --type $kind --notes "Joga Bonito 1.5.1 Qt runtime compatibility hotfix" --private-key $PrivateKey --output releases\stable.json
}

Get-ChildItem -LiteralPath $releaseDir | Select-Object Name, Length
