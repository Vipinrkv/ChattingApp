<#
PowerShell helper to backup Postgres and run Alembic migrations from the `backend` folder.
Usage:
  .\backup_and_migrate.ps1 -DatabaseUrl 'postgresql://user:pass@host:5432/db' -BackupDir './backups'
#>

param(
    [string]$DatabaseUrl = $env:DATABASE_URL,
    [string]$BackupDir = "./backups"
)

if (-not $DatabaseUrl) {
    Write-Host "DATABASE_URL not provided via -DatabaseUrl or env var. Use -DatabaseUrl param."
    exit 2
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$timestamp = Get-Date -Format yyyyMMddTHHmmssZ
$backupFile = Join-Path (Resolve-Path $BackupDir) "db-backup-$timestamp.dump"

Write-Host "Backing up database to: $backupFile"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$toolScript = Join-Path $scriptDir "db_backup_and_migrate.py"

if (Test-Path $toolScript) {
    python $toolScript --database-url $DatabaseUrl --backup-dir $BackupDir
    if ($LASTEXITCODE -ne 0) {
        Write-Error "db_backup_and_migrate.py failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
    exit 0
}

pg_dump $DatabaseUrl --format=custom --file=$backupFile
if ($LASTEXITCODE -ne 0) {
    Write-Error "pg_dump failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "Running Alembic migrations from backend folder (upgrade head)"
$backendDir = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $backendDir

python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Error "Alembic migration failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "Migration succeeded. Backup file retained at: $backupFile"
