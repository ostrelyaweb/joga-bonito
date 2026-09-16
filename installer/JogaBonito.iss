#define MyAppName "Joga Bonito"
#define MyAppVersion "1.5.1"
#define MyAppPublisher "Joga Bonito"
#define MyAppExeName "JogaBonito.exe"
#ifndef SourceDir
#define SourceDir "..\dist\JogaBonito"
#endif
#ifndef ReleaseDir
#define ReleaseDir "..\release-output"
#endif

[Setup]
AppId={{CB2E3B9A-218D-4E7E-98E8-D8EA21358D67}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\JogaBonito
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir={#ReleaseDir}
OutputBaseFilename=JogaBonito-Setup-{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
