@echo off
chcp 65001 >nul
set PYTHONUTF8=1
if "%1"=="--pure" (
  .conda\python.exe -m backend.experiments.run_pure_eval groq %2 %3
) else (
  .conda\python.exe -m backend.experiments.run_full_eval %*
)
