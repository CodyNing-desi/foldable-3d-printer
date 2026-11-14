@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONPATH=%~dp0src;%PYTHONPATH%
python -m unittest discover -s tests -v
if errorlevel 1 exit /b 1
python scripts\run_final_audit.py
if errorlevel 1 exit /b 1
echo ALL V3.1 FINAL TESTS AND VERIFICATIONS PASSED.
