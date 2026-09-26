@echo off
cd /d "D:\DS\VS git code\homelab-postgres\activitywatch"
if not exist logs mkdir logs
echo ===== %date% %time% ===== >> logs\extract_load.log
"D:\Dynamic\Miniforge3Conda\envs\homelab\python.exe" src\extract_load.py >> logs\extract_load.log 2>&1