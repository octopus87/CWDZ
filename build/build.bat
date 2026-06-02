@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

echo ==^> 准备虚拟环境
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
python -m playwright install chromium

echo ==^> PyInstaller 打包
pyinstaller build\cwdz.spec --noconfirm --clean

set DIST_DIR=%CD%\dist\CWDZ
set PW_CACHE=%LOCALAPPDATA%\ms-playwright
if defined PLAYWRIGHT_BROWSERS_PATH set PW_CACHE=%PLAYWRIGHT_BROWSERS_PATH%

if exist "%PW_CACHE%" (
    echo ==^> 复制 Playwright Chromium
    rmdir /s /q "%DIST_DIR%\ms-playwright" 2>nul
    xcopy /E /I /Y "%PW_CACHE%" "%DIST_DIR%\ms-playwright" >nul
) else (
    echo 警告: 未找到 Playwright 浏览器，请执行: playwright install chromium
)

mkdir "%DIST_DIR%\data\.auth" 2>nul
mkdir "%DIST_DIR%\data\downloads" 2>nul
mkdir "%DIST_DIR%\data\output\vouchers" 2>nul

echo.
echo 打包完成:
echo   Windows 入口: dist\CWDZ\CWDZ.exe
echo   可将整个 dist\CWDZ 文件夹压缩后分发
echo.
pause
