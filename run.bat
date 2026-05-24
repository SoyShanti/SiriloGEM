@echo off
title SpotiGem
cd /d C:\Users\Shanticode\Documents\SpotiGem
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
set PYTHONPATH=C:\Users\Shanticode\Documents\SpotiGem

echo.
echo =====================================
echo SpotiGem - Una consola para todos
echo =====================================
echo.

echo [1/4] Matando procesos viejos...
taskkill /f /im python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/4] ACE Step (:8001)...
start "SpotiGem-ACE-Step" /b cmd /c "cd /d C:\Users\Shanticode\Documents\SpotiGem\ace-step-official && uv run acestep-api"
timeout /t 8 /nobreak >nul

echo [3/4] Backend (:8000)...
start "SpotiGem-Backend" /b python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
timeout /t 5 /nobreak >nul

echo [4/4] Frontend (:5173)...
start "SpotiGem-Frontend" /b cmd /c "cd /d C:\Users\Shanticode\Documents\SpotiGem\frontend && npx.cmd vite --host 0.0.0.0 --port 5173"
timeout /t 4 /nobreak >nul

echo.
echo =====================================
echo ^| Todo en esta consola!            ^|
echo ^|                                   ^|
echo ^| ACE Step: http://localhost:8001   ^|
echo ^| Frontend: http://localhost:5173   ^|
echo ^| Backend:  http://localhost:8000   ^|
echo ^|                                   ^|
echo ^| Ctrl+C para detener todo          ^|
echo =====================================
echo.

:loop
timeout /t 10 /nobreak >nul
goto loop
