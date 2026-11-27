@echo off
REM [5-6] Hanabot Docker Launcher
REM Start docker compose and open browser

echo Starting Hanabot Docker container...
docker compose up -d

REM Wait for server to start
timeout /t 3 /nobreak

REM Open browser
echo Opening browser...
start http://localhost:8080

echo.
echo Hanabot is running at http://localhost:8080
echo.
echo To stop: docker compose down
pause
