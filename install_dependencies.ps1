# Check if the virtual environment directory exists
if (-not (Test-Path -Path ".venv" -PathType Container)) {
    Write-Host "Creating virtual environment..."
    python3 -m venv .venv
}

# Activate the virtual environment
. .\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -r requirements.txt

Write-Host "Dependencies installed successfully."
