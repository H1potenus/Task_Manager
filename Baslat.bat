@echo off
cd /d "%~dp0"
set PY=python
if exist "C:\python_314\python.exe" set PY=C:\python_314\python.exe
"%PY%" main.py
if errorlevel 1 pause
