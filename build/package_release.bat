@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\dist"

if exist "CWDZ\CWDZ.exe" (
    echo ==^> 打包 Windows: CWDZ-Windows-x64.zip
    if exist "CWDZ-Windows-x64.zip" del /f "CWDZ-Windows-x64.zip"
    powershell -NoProfile -Command "Compress-Archive -Path 'CWDZ' -DestinationPath 'CWDZ-Windows-x64.zip' -Force"
    dir "CWDZ-Windows-x64.zip"
) else (
    echo 未找到 dist\CWDZ\CWDZ.exe，请先运行 build\build.bat
    exit /b 1
)

echo 完成。输出目录: %CD%
