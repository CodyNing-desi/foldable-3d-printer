@echo off
cd /d "%~dp0"
python tests\test_v3_2_1_collision_suite.py
if errorlevel 1 exit /b 1
python scripts\run_v3_2_1_verification.py
if errorlevel 1 exit /b 1
