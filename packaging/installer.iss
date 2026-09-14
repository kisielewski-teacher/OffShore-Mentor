; Inno Setup script for OffShore Mentor
; Save this file and compile with Inno Setup (ISCC.exe)
[Setup]
AppName=OffShore Mentor
AppVersion=1.0
DefaultDirName={pf}\OffShoreMentor
DefaultGroupName=OffShore Mentor
OutputBaseFilename=OffShoreMentor_Installer
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\OffShoreMentor\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\OffShore Mentor"; Filename: "{app}\OffShoreMentor.exe"
Name: "{group}\Uninstall OffShore Mentor"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\OffShoreMentor.exe"; Description: "Start OffShore Mentor"; Flags: nowait postinstall skipifsilent