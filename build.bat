@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

REM Activate venv
call "%SCRIPT_DIR%venv\Scripts\activate.bat"

REM ── Strip unused tesseract files before bundling ─────────────────────
REM osd.traineddata (11MB) = orientation detection, not needed for OCR
REM *.jar files (~430KB)   = ScrollView debug tool, not needed
echo Removing unused tesseract files...
del /q "%SCRIPT_DIR%tesseract\tessdata\osd.traineddata" 2>nul
del /q "%SCRIPT_DIR%tesseract\tessdata\*.jar" 2>nul

REM ── UPX check ─────────────────────────────────────────────────────────
set "UPX_DIR=%SCRIPT_DIR%upx"
if exist "%UPX_DIR%\upx.exe" (
    echo UPX found — compression enabled.
    set "UPX_ARGS=--upx-dir "%UPX_DIR%""
) else (
    echo WARNING: UPX not found at upx\upx.exe
    echo Download upx.exe from https://github.com/upx/upx/releases
    echo and place it in the upx\ folder for ~40%% smaller output.
    echo Building without UPX...
    set "UPX_ARGS="
)

REM ── Build ──────────────────────────────────────────────────────────────
echo.
echo Building UglyPDF.exe...
echo.

pyinstaller --onedir --windowed --name UglyPDF ^
    --icon icon.ico ^
    --add-data "poppler;poppler" ^
    --add-data "tesseract;tesseract" ^
    --add-data "app;app" ^
    --add-data "icon.ico;." ^
    %UPX_ARGS% ^
    pdf2md_gui.py

echo.
if exist "%SCRIPT_DIR%dist\UglyPDF\UglyPDF.exe" (
    echo Build successful!
    echo Output folder: %SCRIPT_DIR%dist\UglyPDF\
    echo.
    echo Copy the entire dist\UglyPDF\ folder to any Windows machine.
    echo No Python installation required.
) else (
    echo Build may have failed. Check output above.
)
echo.
pause
