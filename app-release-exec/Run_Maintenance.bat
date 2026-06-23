@echo off
chcp 65001 >nul
REM Navigate to the directory where this script lives (app-release-exec/)
cd /d "%~dp0"
cls
echo ================================================
echo   Alif E8 - Enter Hard Maintenance Mode
echo ================================================
echo.
echo STEP-BY-STEP INSTRUCTIONS:
echo   1. This will open maintenance.exe on COM3
echo   2. You will see a menu. Press [1] then [ENTER]
echo      (this selects: Device Control)
echo   3. You will see another menu. Press [1] then [ENTER]
echo      (this selects: Hard maintenance mode)
echo   4. You will see: "Waiting for Target..[RESET Platform]"
echo   5. PRESS THE RESET BUTTON on your Alif board NOW
echo   6. The tool should connect and show:
echo      "Hard maintenance mode"
echo ================================================
echo.
pause
echo.
echo Starting maintenance.exe...
echo.
maintenance.exe -c COM3
echo.
echo ================================================
echo If you saw "Hard maintenance mode" above,
echo you can close this window and tell me to flash the board.
echo ================================================
pause
