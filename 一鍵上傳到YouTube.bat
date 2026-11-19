@echo off
title YouTube Teaching Video Uploader
cd /d "%~dp0"

echo ========================================================
echo   YouTube Teaching Video Uploader
echo ========================================================
echo.

python upload_with_browser.py

echo.
echo ========================================================
echo   Process finished. Press any key to exit...
echo ========================================================
pause >nul
