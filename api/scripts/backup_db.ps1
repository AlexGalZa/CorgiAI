$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = $env:BACKUP_DIR ?? "./backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
pg_dump -h ($env:DATABASE_HOST ?? "localhost") -U ($env:DATABASE_USER ?? "corgi_admin") -d ($env:DATABASE_NAME ?? "corgi") | Out-File "$backupDir/corgi_$timestamp.sql"
Write-Host "Backup complete: corgi_$timestamp.sql"
