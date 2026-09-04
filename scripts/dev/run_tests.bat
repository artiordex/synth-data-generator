@echo off
echo ========================================================
echo  Running Enterprise Test Suites
echo ========================================================
cd /d %~dp0..\..
.\.uv\Scripts\python.exe -m pytest -v\n