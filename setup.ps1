$PYTHON_BIN = $null
foreach ($cmd in @("python3.14", "python3.13", "python3.12", "python3.11", "python3", "python")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $PYTHON_BIN = $cmd
        break
    }
}

if (-not $PYTHON_BIN) {
    Write-Error "A suitable Python interpreter was not found."
    exit 1
}

if (Test-Path ".venv") {
    Remove-Item -Recurse -Force ".venv"
}

& $PYTHON_BIN -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt

Write-Host "Environment ready."
Write-Host "Python used: $PYTHON_BIN"