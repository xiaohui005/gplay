$ErrorActionPreference = "Continue"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Start backend
$be = Start-Process -NoNewWindow -PassThru -FilePath python -WorkingDirectory "$scriptPath\server" -ArgumentList "-m uvicorn src.main:app --port 8008"
Start-Sleep 4

# Start frontend
$fe = Start-Process -NoNewWindow -PassThru -FilePath npx -WorkingDirectory "$scriptPath\frontend" -ArgumentList "vite", "--host", "--port", "5173"

Write-Output "Backend PID=$($be.Id) Frontend PID=$($fe.Id)"
while ($true) { Start-Sleep 10 }
