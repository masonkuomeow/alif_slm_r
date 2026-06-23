@echo off
title Alif Hard Maintenance Mode
cd /d "C:\Users\mason\alif\alif_ml-embedded-evaluation-kit\tools\app-release-exec"
cls
echo ================================================
echo   STEP 1: Enter Hard Maintenance Mode
echo ================================================
echo  This window will open maintenance.exe on COM3.
echo.
echo  Instructions:
echo    1. Press 1 then ENTER  (Device Control)
echo    2. Press 1 then ENTER  (Hard maintenance mode)
echo    3. When you see [RESET Platform], PRESS THE RESET BUTTON on the board
echo    4. Wait for 'Hard maintenance mode' confirmation
echo ================================================
echo.
pause
echo.
echo Starting maintenance.exe ...
echo.
maintenance.exe -c COM3
echo.
echo ================================================
echo   If the above shows 'Hard maintenance mode',
echo   you can close this window and run Step 2.
echo ================================================
pause
