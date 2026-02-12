; Inno Setup Script for Annual Inspection Tracker

#define AppName "Annual Inspection System"
#define AppVersion "1.0.0"
#define AppExeName "AnnualInspectionSystem.exe"
#define AppPublisher "Annual Inspection System"
#define AppURL ""

[Setup]
AppId={{0D4B4C9D-7C4F-4C9F-9B02-6C8B5B2D7A3A}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=output
OutputBaseFilename=AnnualInspectionSetup
Compression=lzma
SolidCompression=yes
SetupIconFile=..\business_management_icon.ico

[Files]
Source: "..\dist_icon\AnnualInspectionSystem\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
