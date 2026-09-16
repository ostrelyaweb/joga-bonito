param(
    [string]$PrivateKey = "",
    [string]$PackageUrl = ""
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

python -m unittest discover -s tests -v
python -m PyInstaller --clean --noconfirm JogaBonito.spec

$releaseDir = Join-Path $PSScriptRoot "release-output"
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
$portable = Join-Path $releaseDir "JogaBonito-Portable-1.5.0.zip"
if (Test-Path -LiteralPath $portable) { Remove-Item -LiteralPath $portable -Force }
Compress-Archive -LiteralPath (Join-Path $PSScriptRoot "dist\JogaBonito") -DestinationPath $portable -CompressionLevel Optimal

$isccCandidates = @(@(
    (Get-Command iscc -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) })
if ($isccCandidates.Count -gt 0) {
    & $isccCandidates[0] (Join-Path $PSScriptRoot "installer\JogaBonito.iss")
} else {
    Write-Warning "Inno Setup not found; portable build was created, installer was skipped."
}

if ($PrivateKey -and $PackageUrl) {
    $installer = Join-Path $releaseDir "JogaBonito-Setup-1.5.0.exe"
    $package = if (Test-Path -LiteralPath $installer) { $installer } else { $portable }
    $kind = if ($package.EndsWith(".exe")) { "installer" } else { "portable" }
    python tools\sign_release.py --package $package --url $PackageUrl --version 1.5.0 --type $kind --notes "Joga Bonito 1.5.0 production release" --private-key $PrivateKey --output releases\stable.json
}

Get-ChildItem -LiteralPath $releaseDir | Select-Object Name, Length
