[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

if ($env:OS -ne 'Windows_NT') {
    throw 'release:windows 只能在 Windows NTFS checkout 執行。'
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$viewerRoot = Split-Path -Parent $projectRoot
$releaseExe = Join-Path $projectRoot 'src-tauri\target\release\experiment-viewer.exe'
$portableExe = Join-Path $viewerRoot 'experiment-viewer.exe'

if ($projectRoot -notmatch '^[A-Za-z]:\\') {
    throw 'release:windows 必須從 Windows 本機 NTFS checkout 執行，不接受 UNC 或 WSL 路徑。'
}

$driveRoot = [System.IO.Path]::GetPathRoot($projectRoot)
$drive = [System.IO.DriveInfo]::new($driveRoot)
if ($drive.DriveFormat -ne 'NTFS') {
    throw "release:windows 必須從 NTFS checkout 執行；目前檔案系統：$($drive.DriveFormat)。"
}

function Invoke-External {
    param(
        [Parameter(Mandatory)]
        [string] $Command,

        [Parameter(Mandatory)]
        [string[]] $Arguments,

        [Parameter(Mandatory)]
        [string] $Label
    )

    Write-Output "執行：$Label"
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label 失敗，exit code：$LASTEXITCODE"
    }
}

function Get-Sha256 {
    param(
        [Parameter(Mandatory)]
        [string] $Path
    )

    $stream = [System.IO.File]::OpenRead($Path)
    try {
        $algorithm = [System.Security.Cryptography.SHA256]::Create()
        try {
            $hashBytes = $algorithm.ComputeHash($stream)
        }
        finally {
            $algorithm.Dispose()
        }
    }
    finally {
        $stream.Dispose()
    }

    return [System.BitConverter]::ToString($hashBytes).Replace('-', '')
}

function Assert-WindowsPe {
    param(
        [Parameter(Mandatory)]
        [string] $Path
    )

    $stream = [System.IO.File]::OpenRead($Path)
    try {
        $reader = [System.IO.BinaryReader]::new($stream)
        try {
            if ($stream.Length -lt 64 -or $reader.ReadUInt16() -ne 0x5A4D) {
                throw '產物缺少有效的 DOS MZ header。'
            }

            $stream.Position = 0x3C
            $peOffset = $reader.ReadUInt32()
            if ($peOffset -gt ($stream.Length - 4)) {
                throw '產物的 PE header offset 超出檔案範圍。'
            }

            $stream.Position = $peOffset
            if ($reader.ReadUInt32() -ne 0x00004550) {
                throw '產物缺少有效的 PE signature。'
            }
        }
        finally {
            $reader.Dispose()
        }
    }
    finally {
        $stream.Dispose()
    }
}

Push-Location $projectRoot
try {
    Invoke-External -Command 'npm.cmd' -Arguments @('ci') -Label '安裝鎖定的前端依賴'
    Invoke-External -Command 'npm.cmd' -Arguments @('test') -Label '執行 Viewer 測試'
    Invoke-External -Command 'cargo.exe' -Arguments @(
        'test',
        '--manifest-path',
        'src-tauri\Cargo.toml'
    ) -Label '執行 Rust/Tauri 測試'
    Invoke-External -Command 'npm.cmd' -Arguments @(
        'run',
        'tauri',
        '--',
        'build',
        '--no-bundle'
    ) -Label '建置 Windows release exe'

    Copy-Item -LiteralPath $releaseExe -Destination $portableExe -Force
    Assert-WindowsPe -Path $portableExe
    $releaseHash = Get-Sha256 -Path $releaseExe
    $portableHash = Get-Sha256 -Path $portableExe
    if ($releaseHash -ne $portableHash) {
        throw 'portable 副本與 release 來源的 SHA-256 不一致。'
    }

    Write-Output "完成：$portableExe"
    Write-Output "SHA256：$portableHash"
}
finally {
    Pop-Location
}
