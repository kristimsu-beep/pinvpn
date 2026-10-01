#define MyAppName "PinVPN"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "PinVPN"
#define MyAppExeName "PinVPN.exe"
#define WireGuardMsi "wireguard-amd64-1.1.1.msi"

[Setup]
AppId={{8A7E1D71-7F4A-4A9B-A9B0-PINV-PVPN1001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\PinVPN

DefaultGroupName=PinVPN

OutputDir=..\installer-output
OutputBaseFilename=PinVPN-Setup

Compression=lzma
SolidCompression=yes

WizardStyle=modern

PrivilegesRequired=admin

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]

Source: "..\dist\PinVPN.exe"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

Source: "{#WireGuardMsi}"; \
    DestDir: "{app}"; \
    Flags: deleteafterinstall

[Icons]

Name: "{autoprograms}\PinVPN"; \
    Filename: "{app}\{#MyAppExeName}"

Name: "{autodesktop}\PinVPN"; \
    Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

[Tasks]

Name: "desktopicon"; \
    Description: "Создать ярлык на рабочем столе"; \
    GroupDescription: "Дополнительные ярлыки:"

[Run]

Filename: "msiexec.exe"; \
    Parameters: "/i ""{app}\{#WireGuardMsi}"" DO_NOT_LAUNCH=1 /qn /norestart"; \
    StatusMsg: "Установка компонентов PinVPN..."; \
    Flags: waituntilterminated

Filename: "{app}\{#MyAppExeName}"; \
    Description: "Запустить PinVPN"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]

Type: files
Name: "{app}\{#WireGuardMsi}"

