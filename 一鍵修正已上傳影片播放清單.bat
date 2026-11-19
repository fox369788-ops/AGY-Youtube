@echo off
title Fix YouTube Playlists
cd /d "%~dp0"

echo ========================================================
echo   YouTube Playlists Auto Assignment Tool
echo ========================================================
echo.

python manage_playlists.py

echo.
echo ========================================================
echo   Process finished. Press any key to exit...
echo ========================================================
pause >nul
