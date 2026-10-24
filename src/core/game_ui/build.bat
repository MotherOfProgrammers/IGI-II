@echo off
g++ -O2 -s -mwindows -static -o IGI_Launcher.exe main.cpp -lgdiplus -lgdi32 -lwinmm -lcomdlg32 -lshell32 -luser32 -lole32
if errorlevel 1 (echo BUILD FAILED) else (echo Done: IGI_Launcher.exe)
pause
