@echo off
cd /d d:\Github\job-agent
if not exist "logs" mkdir "logs"
echo [%date% %time%] Running daily reminder (App-first, fallback email)...>> "logs\daily_email.log"
.venv\Scripts\python.exe -m job_agent.cli daily-cycle --skip-sync --skip-edge --skip-prefilter --skip-llm --notify >> "logs\daily_email.log" 2>&1
