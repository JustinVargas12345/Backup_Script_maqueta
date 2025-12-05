#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Script para ejecutar backups dentro de un contenedor Docker de forma segura.
    Gestiona contraseñas y tokens sin exponerlos en archivos ni en el log de comandos.

.DESCRIPTION
    1. Solicita credenciales de forma interactiva (sin mostrar en pantalla).
    2. Construye la imagen Docker si no existe.
    3. Ejecuta el contenedor con las variables de entorno inyectadas.
    4. Limpia variables sensibles después de ejecutar.

.PARAMETER DbType
    Tipo de base de datos: postgres, mysql, mongo, sqlserver

.PARAMETER Host
    Host de la BD (default: localhost)

.PARAMETER Port
    Puerto de la BD (default: automático según DbType)

.PARAMETER Database
    Nombre de la BD a respaldar

.PARAMETER User
    Usuario para conectar

.PARAMETER ImageName
    Nombre de la imagen Docker a usar (default: backup_script:local)

.PARAMETER ImageTag
    Tag de la imagen (default: latest)

.PARAMETER BuildIfMissing
    Si es $true, construye la imagen si no existe (default: $true)

.EXAMPLE
    # Ejecutar backup de Postgres:
    .\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres

    # Ejecutar backup de MySQL con compresión y notificación:
    .\scripts\run_backup_docker.ps1 -DbType mysql -Database mydb -User root -Compress zip -NotifySlack

.NOTES
    - Las contraseñas se solicitan de forma segura sin eco en pantalla.
    - Las variables de entorno se inyectan al contenedor y se limpian después.
    - Los backups se guardan en ./backups dentro del contenedor (mapeado al host).
#>

param (
    [Parameter(Mandatory = $true)]
    [ValidateSet("postgres", "mysql", "mongo", "sqlserver")]
    [string]$DbType,

    [Parameter(Mandatory = $true)]
    [string]$Database,

    [Parameter(Mandatory = $true)]
    [string]$User,

    [string]$Host = "host.docker.internal",

    [int]$Port = 0,  # 0 = default según DbType

    [string]$ImageName = "backup_script",
    [string]$ImageTag = "local",

    [bool]$BuildIfMissing = $true,

    [string]$Compress = "",  # zip, tar, gz, etc.
    [bool]$NotifySlack = $false,
    [string]$Cloud = "",  # s3, gcs, azure

    [switch]$SkipBinaryCheck,
    [switch]$SkipConnectionCheck
)

# Variables globales
$ImageFullName = "$($ImageName):$($ImageTag)"
$RepositoryRoot = (Get-Item "$PSScriptRoot/..").FullName
$BackupsDir = Join-Path $RepositoryRoot "backups"

# Crear directorio de backups si no existe
if (-not (Test-Path $BackupsDir)) {
    New-Item -ItemType Directory -Path $BackupsDir -Force | Out-Null
    Write-Host "✓ Directorio de backups creado: $BackupsDir" -ForegroundColor Green
}

# Función para solicitar contraseña de forma segura
function Get-SecureInput {
    param([string]$Prompt)
    $SecureString = Read-Host -Prompt $Prompt -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureString)
    return [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

# Función para verificar si la imagen Docker existe
function Test-DockerImage {
    param([string]$ImageName)
    $Images = docker images --format "{{.Repository}}:{{.Tag}}" 2>$null | Select-String $ImageName
    return $null -ne $Images
}

# Función para construir la imagen
function Build-DockerImage {
    param([string]$ImageName, [string]$Path)
    Write-Host "📦 Construyendo imagen Docker: $ImageName" -ForegroundColor Cyan
    $FullImageName = "$($ImageName):local"
    docker build -t $FullImageName $Path
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Error construyendo imagen Docker" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Imagen Docker construida exitosamente" -ForegroundColor Green
}

# Verificar Docker
Write-Host "🔍 Verificando Docker..." -ForegroundColor Cyan
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker no está instalado o no está en el PATH" -ForegroundColor Red
    exit 1
}

# Verificar/construir imagen
if (-not (Test-DockerImage $ImageFullName)) {
    if ($BuildIfMissing) {
        Build-DockerImage $ImageName $RepositoryRoot
    }
    else {
        Write-Host "❌ Imagen Docker $ImageFullName no existe. Use -BuildIfMissing `$true" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "✓ Imagen Docker encontrada: $ImageFullName" -ForegroundColor Green
}

# Solicitar contraseña de forma segura
Write-Host ""
Write-Host "🔐 Solicitud de credenciales (no se mostrarán en pantalla)" -ForegroundColor Cyan
$Password = Get-SecureInput "Contraseña para $User (en $DbType): "

if ([string]::IsNullOrWhiteSpace($Password)) {
    Write-Host "❌ Contraseña vacía. Cancelando." -ForegroundColor Red
    exit 1
}

# Solicitar secreto de notificación si --notify-slack está habilitado
$NotifySecret = ""
if ($NotifySlack) {
    $PromptNotify = Read-Host "¿Deseas usar notificaciones webhook? (s/n)"
    if ($PromptNotify -eq "s" -or $PromptNotify -eq "S") {
        $NotifySecret = Get-SecureInput "Secreto/token de notificación (opcional, Enter para omitir): "
    }
}

# Determinar puerto por defecto si no se especifica
if ($Port -eq 0) {
    switch ($DbType) {
        "postgres" { $Port = 5432; break }
        "mysql" { $Port = 3306; break }
        "mongo" { $Port = 27017; break }
        "sqlserver" { $Port = 1433; break }
    }
}

# Construir comando del contenedor
Write-Host ""
Write-Host "🚀 Ejecutando backup en contenedor Docker..." -ForegroundColor Cyan

$DockerRunArgs = @(
    "run",
    "--rm",
    "-it",
    "-e", "PGPASSWORD=$Password",  # Para Postgres
    "-e", "DB_PASSWORD=$Password",  # Variable genérica para la BD
    "-v", "$($BackupsDir):/app/backups",
    "-w", "/app",
    $ImageFullName,
    "backup",
    "run",
    "--dbtype", $DbType,
    "--host", $Host,
    "--port", $Port.ToString(),
    "--user", $User,
    "--password", $Password,
    "--database", $Database,
    "--outdir", "backups"
)

# Añadir opciones opcionales
if (-not [string]::IsNullOrWhiteSpace($Compress)) {
    $DockerRunArgs += "--compress", $Compress
}

if ($NotifySlack) {
    $DockerRunArgs += "--notify-slack"
    if (-not [string]::IsNullOrWhiteSpace($NotifySecret)) {
        # Insertar NOTIFY_SECRET después de las variables de entorno existentes
        $DockerRunArgs = $DockerRunArgs[0..5] + @("-e", "NOTIFY_SECRET=$NotifySecret") + $DockerRunArgs[6..($DockerRunArgs.Length-1)]
    }
}

if ($SkipBinaryCheck) {
    $DockerRunArgs += "--skip-binary-check"
}

if ($SkipConnectionCheck) {
    $DockerRunArgs += "--skip-connection-check"
}

if (-not [string]::IsNullOrWhiteSpace($Cloud)) {
    $DockerRunArgs += "--cloud", $Cloud
}

# Ejecutar
$ExitCode = 0
try {
    & docker $DockerRunArgs
    $ExitCode = $LASTEXITCODE
}
catch {
    Write-Host "❌ Error ejecutando contenedor: $_" -ForegroundColor Red
    $ExitCode = 1
}
finally {
    # IMPORTANTE: Limpiar variables sensibles
    $null = Remove-Item -Path Env:PGPASSWORD -ErrorAction SilentlyContinue
    $null = Remove-Item -Path Env:DB_PASSWORD -ErrorAction SilentlyContinue
    if (-not [string]::IsNullOrWhiteSpace($NotifySecret)) {
        $null = Remove-Item -Path Env:NOTIFY_SECRET -ErrorAction SilentlyContinue
    }
}

if ($ExitCode -eq 0) {
    Write-Host ""
    Write-Host "✅ Backup completado exitosamente" -ForegroundColor Green
    Write-Host "📁 Los archivos están en: $BackupsDir" -ForegroundColor Cyan
}
else {
    Write-Host ""
    Write-Host "❌ Backup falló con código de salida: $ExitCode" -ForegroundColor Red
    exit $ExitCode
}
