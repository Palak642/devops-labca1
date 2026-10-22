$ErrorActionPreference = "Stop"

$version = "8.30.1"
$architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
if ($architecture -ne [System.Runtime.InteropServices.Architecture]::X64) {
    throw "This installer currently supports Windows x64 only; detected $architecture."
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$installDirectory = Join-Path $projectRoot ".tools"
$temporaryDirectory = Join-Path $env:TEMP ("gitleaks-install-" + [guid]::NewGuid().ToString("N"))
$archiveName = "gitleaks_${version}_windows_x64.zip"
$archivePath = Join-Path $temporaryDirectory $archiveName
$checksumsPath = Join-Path $temporaryDirectory "checksums.txt"
$releaseBase = "https://github.com/gitleaks/gitleaks/releases/download/v$version"

function Save-ReleaseFile {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) {
        & $curl.Source --fail --location --silent --show-error --retry 2 `
            --retry-all-errors --connect-timeout 15 --max-time 180 `
            --output $Destination $Uri
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $Destination)) {
            return
        }
        Remove-Item -LiteralPath $Destination -Force -ErrorAction SilentlyContinue
    }

    try {
        Invoke-WebRequest -Uri $Uri -OutFile $Destination -TimeoutSec 180
    }
    catch {
        throw "Could not download the official Gitleaks release from GitHub. Check internet, proxy, or firewall access to github.com and release assets, then rerun this installer. $($_.Exception.Message)"
    }
}

try {
    New-Item -ItemType Directory -Path $temporaryDirectory | Out-Null
    Save-ReleaseFile -Uri "$releaseBase/$archiveName" -Destination $archivePath
    Save-ReleaseFile -Uri "$releaseBase/gitleaks_${version}_checksums.txt" -Destination $checksumsPath

    $checksumEntry = Get-Content -LiteralPath $checksumsPath |
        Where-Object { $_ -match ("\s" + [regex]::Escape($archiveName) + "$") } |
        Select-Object -First 1
    if (-not $checksumEntry) {
        throw "No published checksum found for $archiveName."
    }

    $expectedChecksum = ($checksumEntry -split "\s+")[0].ToLowerInvariant()
    $actualChecksum = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualChecksum -ne $expectedChecksum) {
        throw "Gitleaks archive checksum verification failed."
    }

    $extractDirectory = Join-Path $temporaryDirectory "extracted"
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractDirectory
    $executable = Join-Path $extractDirectory "gitleaks.exe"
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw "The downloaded archive did not contain gitleaks.exe."
    }

    New-Item -ItemType Directory -Path $installDirectory -Force | Out-Null
    Copy-Item -LiteralPath $executable -Destination (Join-Path $installDirectory "gitleaks.exe") -Force
    Write-Output "Installed and checksum-verified Gitleaks $version at $installDirectory."
}
finally {
    if (Test-Path -LiteralPath $temporaryDirectory) {
        Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force
    }
}
