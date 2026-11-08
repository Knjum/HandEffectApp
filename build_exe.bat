@echo off
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Khong tim thay venv\Scripts\python.exe.
    echo Hay tao venv va cai requirements.txt truoc.
    exit /b 1
)

"venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm "HandEffectApp.spec"
if errorlevel 1 (
    echo.
    echo Dong goi that bai. Hay cai requirements-build.txt va thu lai.
    exit /b 1
)

echo.
echo Da dong goi: dist\HandEffectApp\HandEffectApp.exe
endlocal
