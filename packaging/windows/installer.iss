; Installateur Windows (Inno Setup 6), à partir de dist\Equation-Geographique produit par PyInstaller.
; Construction : ISCC.exe /DAppVersion=1.0.0 packaging\windows\installer.iss

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6B1E4F0A-2C7D-4E58-9A3B-5D8C1F2E7A90}
AppName=Équation géographique
AppVersion={#AppVersion}
AppPublisher=Bernard Brosseau-Villeneuve
DefaultDirName={autopf}\Équation géographique
DefaultGroupName=Équation géographique
DisableProgramGroupPage=yes
; Installation pour l'utilisateur courant, sans droits administrateur.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist
OutputBaseFilename=Equation-Geographique-Windows-Installateur
SetupIconFile=..\..\src\equation_geographique\data\icon.ico
UninstallDisplayIcon={app}\Equation-Geographique.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\Equation-Geographique\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Équation géographique"; Filename: "{app}\Equation-Geographique.exe"
Name: "{autodesktop}\Équation géographique"; Filename: "{app}\Equation-Geographique.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Equation-Geographique.exe"; Description: "{cm:LaunchProgram,Équation géographique}"; Flags: nowait postinstall skipifsilent
