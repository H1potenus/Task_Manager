$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = "python"
if (Test-Path "C:\python_314\python.exe") { $py = "C:\python_314\python.exe" }

# Simge yoksa üret (Pillow gerekir)
if (-not (Test-Path "$PSScriptRoot\assets\icon.ico")) {
  & $py -m pip install --upgrade pillow
  & $py "$PSScriptRoot\tools\make_icon.py"
}

& $py -m pip install --upgrade pyinstaller customtkinter matplotlib
& $py -m PyInstaller --noconfirm --clean --onefile --windowed --name TaskPlannerPomodoro `
  --icon "$PSScriptRoot\assets\icon.ico" `
  --add-data "$PSScriptRoot\assets\icon.ico;assets" `
  --collect-all customtkinter --hidden-import matplotlib.backends.backend_tkagg `
  --distpath "$PSScriptRoot\dist" --workpath "$PSScriptRoot\build" --specpath "$PSScriptRoot\build" main.py
Copy-Item "$PSScriptRoot\dist\TaskPlannerPomodoro.exe" "$PSScriptRoot\TaskPlannerPomodoro.exe" -Force

$desktop = [Environment]::GetFolderPath("Desktop")
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut("$desktop\Task Planner - Pomodoro Timer.lnk")
$lnk.TargetPath = "$PSScriptRoot\TaskPlannerPomodoro.exe"
$lnk.WorkingDirectory = $PSScriptRoot
$lnk.IconLocation = "$PSScriptRoot\assets\icon.ico"
$lnk.Save()
Write-Host "TAMAM: TaskPlannerPomodoro.exe ve masaustu kisayolu olusturuldu." -ForegroundColor Green
