param(
    [int]$Port = 8787
)

$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $command) { throw 'Python was not found.' }
    $python = $command.Source
}

Write-Host "Local demo OCR server: http://127.0.0.1:$Port/v1"
Write-Host 'Press Ctrl+C to stop.'
& $python (Join-Path $PSScriptRoot 'demo_ocr_server.py') --port $Port
