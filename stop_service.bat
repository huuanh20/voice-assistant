@echo off
title Dung AI Voice Assistant
echo Dang dung tien trinh Voice Assistant chay ngam...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*background_service.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo [✓] Da dung Tro ly AI thanh cong!
timeout /t 2 >nul
