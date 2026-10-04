; Installateur Windows (Inno Setup 6), à partir de dist\Mireille-Tuto produit par PyInstaller.
; Construction : ISCC.exe /DAppVersion=1.0.0 packaging\windows\installer.iss

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6B1E4F0A-2C7D-4E58-9A3B-5D8C1F2E7A90}
AppName=Mireille Tuto
AppVersion={#AppVersion}
AppPublisher=Bernard Brosseau-Villeneuve
DefaultDirName={autopf}\Mireille Tuto
DefaultGroupName=Mireille Tuto
DisableProgramGroupPage=yes
; Installation pour l'utilisateur courant, sans droits administrateur.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist
OutputBaseFilename=Mireille-Tuto-Windows-Installateur
SetupIconFile=..\..\src\mireille_tuto\data\icon.ico
UninstallDisplayIcon={app}\Mireille-Tuto.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\Mireille-Tuto\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Mireille Tuto"; Filename: "{app}\Mireille-Tuto.exe"
Name: "{autodesktop}\Mireille Tuto"; Filename: "{app}\Mireille-Tuto.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Mireille-Tuto.exe"; Description: "{cm:LaunchProgram,Mireille Tuto}"; Flags: nowait postinstall skipifsilent
