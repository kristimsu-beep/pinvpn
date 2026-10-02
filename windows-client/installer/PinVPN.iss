#define MyAppName "PinVPN"
#define MyAppVersion "1.0.2"
#define MyAppPublisher "PinVPN"

#define MyAppExeName "PinVPN.exe"
#define MyServiceExeName "PinVPNService.exe"
#define WireGuardMsi "wireguard-amd64-1.1.1.msi"

[Setup]

AppId={{8A7E1D71-7F4A-4A9B-A9B0-123456789001}

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

Source: "..\dist\PinVPNService.exe"; \
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
    StatusMsg: "Установка VPN-компонента..."; \
    Flags: waituntilterminated runhidden

Filename: "{app}\{#MyServiceExeName}"; \
    Parameters: "install"; \
    StatusMsg: "Установка службы PinVPN..."; \
    Flags: waituntilterminated runhidden

Filename: "{sys}\sc.exe"; \
    Parameters: "config PinVPNService start= auto"; \
    StatusMsg: "Настройка службы PinVPN..."; \
    Flags: waituntilterminated runhidden

Filename: "{sys}\sc.exe"; \
    Parameters: "start PinVPNService"; \
    StatusMsg: "Запуск службы PinVPN..."; \
    Flags: waituntilterminated runhidden

Filename: "{app}\{#MyAppExeName}"; \
    Description: "Запустить PinVPN"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]

Filename: "{app}\{#MyServiceExeName}"; \
    Parameters: "stop"; \
    Flags: waituntilterminated runhidden; \
    RunOnceId: "StopPinVPNService"

Filename: "{app}\{#MyServiceExeName}"; \
    Parameters: "remove"; \
    Flags: waituntilterminated runhidden; \
    RunOnceId: "RemovePinVPNService"
