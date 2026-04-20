if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "Missing package environment. Run .\setup.ps1 first."
    exit 1
}

$DATE = if ($args.Count -gt 0) { $args[0] } else { "2024-05-02" }

if ($DATE -eq "all") {
    .\.venv\Scripts\python ".\run_local_eval.py" --strategy ".\run_strategy.py" --split test_sample --report-dir local_test_report
} else {
    .\.venv\Scripts\python ".\run_local_eval.py" --strategy ".\run_strategy.py" --split test_sample --report-dir local_test_report --date $DATE
}