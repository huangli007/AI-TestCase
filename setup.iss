; TestCase Agent 安装程序脚本(Inno Setup 7)
; 用法: ISCC.exe TestCaseAgent.iss
; 产物: installer/TestCaseAgent-Setup.exe

#define MyAppName "TestCase Agent"
#define MyAppNameCN "AI 测试用例生成器"
#define MyAppVersion "1.0.0"
#define MyAppExeName "TestCaseAgent.exe"
#define MyAppId "{{B8F3A2C1-4E5D-4A9B-9C3E-2F6A1D7E8B4A}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=TestCaseAgent
AppVerName={#MyAppName}
DefaultDirName={autopf}\TestCaseAgent
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=TestCaseAgent-Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; 免管理员权限:默认安装到用户目录
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion=1.0.0
VersionInfoProductName=TestCase Agent
; 关闭自动重启等打扰
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; 打包产物全部复制
Source: "dist_final\TestCaseAgent\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\TestCaseAgent"
