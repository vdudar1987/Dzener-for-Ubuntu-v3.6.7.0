@echo off
cls
echo Loading...
timeout 3 > nul
cls
echo Loading.....
cd /D "%~dp0"
move /y dzener.exe.txt dzener.exe > nul 2>&1
start dzener.exe %1
cls	