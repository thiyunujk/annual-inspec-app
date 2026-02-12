# get_share_path.ps1
$path = Read-Host "Enter server share UNC path (example: \\SERVER\Share\annual inspection software data)"
if (-not ($path -match '^\\\\[^\\]+\\[^\\]+')) {
    Write-Host "Invalid UNC path. It should look like \\SERVER\Share\Folder" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $path)) {
    Write-Host "Path not reachable: $path" -ForegroundColor Yellow
    Write-Host "Check the server name, share name, and permissions." -ForegroundColor Yellow
    exit 1
}
Write-Host "OK: $path" -ForegroundColor Green
