# Run the editor (media-editor) once, unattended. Used by Windows Task Scheduler or by hand.
#   powershell -ExecutionPolicy Bypass -File scripts\run-agent.ps1
# Permissions come from .claude\settings.json (no --dangerously-skip-permissions).
# Log: logs\run_YYYYMMDD_HHMMSS.log
# 1. No notify settings -> stop before writing anything (nobody would hear about the result).
# 2. Timeout / start error / editor did not finish -> one failure notice (scripts\notify.py failure).
# Keep this file ASCII only: Windows PowerShell 5.1 reads BOM-less scripts as Shift-JIS.

param(
    [string]$Agent = "media-editor",
    [int]$TimeoutSec = 5400
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8  # python prints UTF-8 (scripts/_env.py)
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
New-Item -ItemType Directory -Force (Join-Path $Root "logs") | Out-Null
New-Item -ItemType Directory -Force (Join-Path $Root "work") | Out-Null
$Log = Join-Path $Root ("logs\run_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")

& python scripts/notify.py check | Tee-Object -FilePath $Log
if ($LASTEXITCODE -ne 0) {
    "[run-agent] STOP: notify settings missing in .env.local (see .env.local.sample)" | Tee-Object -FilePath $Log -Append
    exit 3
}

function Send-Failure([string]$Reason, [string]$Detail) {
    & python scripts/notify.py failure $Reason $Log $Detail | Tee-Object -FilePath $Log -Append
}

$RunId = (& python scripts/reflection.py start --slug $Agent --trigger scheduler).Trim()
"[run-agent] $Agent RUN_ID=$RunId timeout=${TimeoutSec}s" | Tee-Object -FilePath $Log -Append

$Prompt = "Read .claude/agents/$Agent.md and follow its rules exactly. Your AGENT_RUN_ID is $RunId (already created; do not create another). Reply in Japanese."

# claude is an npm shim (claude.cmd), so start it through cmd.exe
try {
    $Proc = Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c claude -p `"$Prompt`" --output-format text" `
        -NoNewWindow -PassThru `
        -RedirectStandardOutput "$Log.out" -RedirectStandardError "$Log.err"
} catch {
    & python scripts/reflection.py fail $RunId "start failed: $_"
    Send-Failure "start" "$_"
    exit 1
}

if (-not $Proc.WaitForExit($TimeoutSec * 1000)) {
    Stop-Process -Id $Proc.Id -Force
    & python scripts/reflection.py fail $RunId "timeout"
    "[run-agent] TIMEOUT after ${TimeoutSec}s" | Tee-Object -FilePath $Log -Append
    Send-Failure "timeout" "$([int]($TimeoutSec / 60)) min"
    exit 124
}

Get-Content "$Log.out", "$Log.err" -ErrorAction SilentlyContinue | Add-Content $Log
Remove-Item "$Log.out", "$Log.err" -ErrorAction SilentlyContinue
$Status = (& python scripts/reflection.py status $RunId).Trim()
"[run-agent] done (exit $($Proc.ExitCode), status $Status)" | Tee-Object -FilePath $Log -Append

if ($Proc.ExitCode -ne 0 -or $Status -ne "completed") {
    if ($Status -eq "running") { & python scripts/reflection.py fail $RunId "ended without Step Final (exit $($Proc.ExitCode))" }
    Send-Failure "unfinished" "exit $($Proc.ExitCode), status $Status"
    exit 1
}
exit 0
