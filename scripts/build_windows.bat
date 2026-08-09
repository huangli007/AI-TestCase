@echo off
rem ============================================================
rem  Windows 一键打包:生成 dist\TestCaseAgent\TestCaseAgent.exe
rem  用法:双击运行,或命令行执行 build_windows.bat
rem ============================================================
setlocal
cd /d "%~dp0.."

echo [1/3] 生成应用图标...
python tools\make_icon.py || goto :err

echo [2/3] PyInstaller 打包(约 2~5 分钟)...
python -m PyInstaller TestCaseAgent.spec --noconfirm --clean || goto :err

echo [3/3] 完成!
echo.
echo  可执行文件: dist\TestCaseAgent\TestCaseAgent.exe
echo  可选:用 Inno Setup 将 dist\TestCaseAgent\ 目录打成 setup.exe 安装包
goto :eof

:err
echo 打包失败,请检查上方错误信息。
exit /b 1
