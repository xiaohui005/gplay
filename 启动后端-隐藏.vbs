Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

root = fso.GetParentFolderName(WScript.ScriptFullName)
serverDir = root & "\server"

cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command " & Chr(34) & _
  "$pidLine = netstat -ano | Select-String ':8008.*LISTEN' | Select-Object -First 1; " & _
  "if ($pidLine) { $parts = ($pidLine.Line -replace '\s+', ' ').Trim().Split(' '); taskkill /F /PID $parts[-1] | Out-Null }; " & _
  "Start-Sleep 2; " & _
  "Start-Process -WindowStyle Hidden -FilePath python -ArgumentList '-m','uvicorn','src.main:app','--port','8008' -WorkingDirectory '" & serverDir & "'" & _
  Chr(34)

shell.Run cmd, 0, False
