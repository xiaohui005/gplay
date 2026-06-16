@echo off
set "ROOT=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$pidLine = netstat -ano | Select-String ':8008.*LISTEN' | Select-Object -First 1; if ($pidLine) { $parts = ($pidLine.Line -replace '\s+', ' ').Trim().Split(' '); taskkill /F /PID $parts[-1] | Out-Null }; Start-Sleep 2; Start-Process -WindowStyle Hidden -FilePath python -ArgumentList '-m','uvicorn','src.main:app','--port','8008' -WorkingDirectory '%ROOT%server'"
exit /b 0
