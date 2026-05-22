; Inno Setup script for CodexSwitch
; https://jrsoftware.org/isinfo.php

#define AppName "CodexSwitch"
#define AppVersion "1.0"
#define AppPublisher "CodexSwitch"
#define AppURL "https://github.com/lvjiawei369/CodexSwitch"
#define AppExeName "CodexSwitch.exe"

[Setup]
AppId={{6B3C1A2D-4E5F-4A8B-9C0D-1E2F3A4B5C6D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=installer_output
OutputBaseFilename=CodexSwitch-Setup
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
; 安装完成后自动启动
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
english.WelcomeLabel2=This will install [name/ver] on your computer.%n%nCodexSwitch lets you use DeepSeek as the AI backend for Codex.%n%nIt is recommended that you close all other applications before continuing.

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startupicon"; Description: "Start CodexSwitch when Windows &starts"; GroupDescription: "Startup:"

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM {#AppExeName}"; Flags: runhidden
