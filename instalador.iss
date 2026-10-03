[Setup]
AppName=Universal Media Downloader Pro
AppVersion=1.0.0
AppVerName=Universal Media Downloader Pro 1.0.0
VersionInfoVersion=1.0.0.0
VersionInfoProductName=Universal Media Downloader Pro
VersionInfoProductVersion=1.0.0
VersionInfoDescription=Instalador de Universal Media Downloader Pro
AppPublisher=Sergio
; SPDX-License-Identifier: GPL-3.0-only
LicenseFile=LICENSE
DefaultDirName={autopf}\Universal Media Downloader
DefaultGroupName=Universal Media Downloader
UninstallDisplayIcon={app}\app_descargador.exe
OutputDir=dist_instalador
OutputBaseFilename=Instalador_UniversalDownloader_v1.0
SetupIconFile=icono.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "dist\app_descargador.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icono.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Universal Media Downloader"; Filename: "{app}\app_descargador.exe"; IconFilename: "{app}\icono.ico"
Name: "{group}\Desinstalar"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Universal Media Downloader"; Filename: "{app}\app_descargador.exe"; IconFilename: "{app}\icono.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\app_descargador.exe"; Description: "Ejecutar Universal Media Downloader"; Flags: nowait postinstall skipifsilent
