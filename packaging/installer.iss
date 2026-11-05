; Inno Setup script for OffShore Mentor
; Save this file and compile with Inno Setup (ISCC.exe)
[Setup]
AppName=OffShore Mentor
AppVersion=1.0.0
DefaultDirName={pf}\OffShoreMentor
DefaultGroupName=OffShore Mentor
OutputBaseFilename=OffShoreMentor_Installer
Compression=lzma
SolidCompression=yes
LicenseFile=..\LICENSE.txt
SetupIconFile=..\assets\icon.ico
; Optional installer code signing (requires a purchased code-signing
; certificate). Uncomment and set up a "mycert" SignTool in the Inno Setup
; Compiler (Tools > Configure Sign Tools), or pass one at compile time:
;   ISCC.exe /Smycert=$qsigntool.exe sign /f $qC:\path\cert.pfx$q /p $qPASSWORD$q /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $f$q installer.iss
; SignTool=mycert

[Files]
Source: "dist\OffShoreMentor\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\OffShore Mentor"; Filename: "{app}\OffShoreMentor.exe"
Name: "{group}\Uninstall OffShore Mentor"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\OffShoreMentor.exe"; Description: "Start OffShore Mentor"; Flags: nowait postinstall skipifsilent