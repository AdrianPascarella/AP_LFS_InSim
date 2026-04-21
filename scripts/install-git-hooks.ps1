# PowerShell script to set hooks path
if (-not (Test-Path -Path .githooks -PathType Container)) {
    Write-Error ".githooks directory not found."
    exit 1
}

git config core.hooksPath .githooks
if ($LASTEXITCODE -eq 0) {
    Write-Output "Git hooks path set to .githooks"
} else {
    Write-Error "Failed to set git hooks path"
    exit 1
}
