[Setup]
AppName=HandMouse
AppVersion=1.0
AppPublisher=HandMouse
DefaultDirName={autopf}\HandMouse
DefaultGroupName=HandMouse
OutputDir=dist
OutputBaseFilename=HandMouseSetup
SetupIconFile=assets\logo\hand_gesture_icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\main\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\HandMouse"; Filename: "{app}\main.exe"
Name: "{group}\Uninstall HandMouse"; Filename: "{uninstallexe}"
Name: "{commondesktop}\HandMouse"; Filename: "{app}\main.exe"

[Run]
Filename: "{app}\main.exe"; Description: "Launch HandMouse"; Flags: postinstall nowait skipifsilent
