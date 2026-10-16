# Silent Hill DS+: puts your own copy of the game into the port folder.
# Put your .bin and .cue (or a .zip with them) into the "game" folder,
# then double-click prepare.bat.
$ErrorActionPreference = 'Stop'

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Game = Join-Path $Here 'game'
$Port = Join-Path (Join-Path $Here 'ports') 'silent-hill-rgds-plus'
$Dest = Join-Path $Port 'gamedata'
$Work = Join-Path $Game 'unpacked'
$UsaSha1 = '34278d31d9b9b12b3b5db5e45bcbe548991ecbc7'

function Fail($Message) {
    Write-Host ''
    Write-Host $Message
    Write-Host ''
    exit 1
}

function Files($Path, $Extensions) {
    @(Get-ChildItem -LiteralPath $Path -File -Recurse -Force | Where-Object { $Extensions -contains $_.Extension.ToLower() })
}

if (-not (Test-Path -LiteralPath (Join-Path $Port 'SilentHillPC')) -or -not (Test-Path -LiteralPath $Dest)) {
    Fail "I can't find ports\silent-hill-rgds-plus next to this script. Run it from the unpacked release folder."
}
New-Item -ItemType Directory -Force -Path $Game | Out-Null

# A zipped image is unpacked first.
$zips = @(Get-ChildItem -LiteralPath $Game -File -Force | Where-Object { $_.Extension.ToLower() -eq '.zip' })
if ($zips.Count -gt 1) { Fail 'There is more than one .zip in the game folder. Leave only the one with Silent Hill.' }
if ($zips.Count -eq 1) {
    Write-Host "Unpacking $($zips[0].Name)..."
    if (Test-Path -LiteralPath $Work) { Remove-Item -LiteralPath $Work -Recurse -Force }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    try { [System.IO.Compression.ZipFile]::ExtractToDirectory($zips[0].FullName, $Work) }
    catch { Fail "Could not unpack $($zips[0].Name)." }
}

$bins = Files $Game @('.bin')
if ($bins.Count -eq 0) {
    $other = Files $Game @('.chd', '.pbp', '.iso', '.7z', '.rar')
    if ($other.Count -gt 0) {
        Fail "$($other[0].Name) can't be used as it is. The game needs a BIN/CUE image. A CHD can be converted with chdman: chdman extractcd -i `"Silent Hill (USA).chd`" -o `"Silent Hill (USA).cue`""
    }
    Fail 'No game found. Put your Silent Hill .bin and .cue (or a .zip with them) into the game folder and run this again.'
}
if ($bins.Count -gt 1) { Fail 'There is more than one .bin in the game folder. Leave only your Silent Hill image.' }
$bin = $bins[0]
$name = [System.IO.Path]::GetFileNameWithoutExtension($bin.Name)

Write-Host "Checking $name.bin..."
if ((Get-FileHash -Algorithm SHA1 -LiteralPath $bin.FullName).Hash.ToLower() -eq $UsaSha1) {
    Write-Host 'This is the North American disc (SLUS-00707 v1.1).'
} else {
    Write-Host 'This is another version of the disc. The port is made for the North American disc (SLUS-00707 v1.1).'
}

Write-Host 'Copying it into the port folder...'
Get-ChildItem -LiteralPath $Dest -File -Force | Where-Object { @('.bin', '.cue') -contains $_.Extension.ToLower() } | Remove-Item -Force
$target = Join-Path $Dest "$name.bin"
try {
    if (Test-Path -LiteralPath $Work) {
        Move-Item -LiteralPath $bin.FullName -Destination $target
        Remove-Item -LiteralPath $Work -Recurse -Force
    } else {
        Copy-Item -LiteralPath $bin.FullName -Destination $target
    }
} catch { Fail 'Could not copy the game. Is there enough free space?' }
$cue = "FILE `"$name.bin`" BINARY`r`n  TRACK 01 MODE2/2352`r`n    INDEX 01 00:00:00`r`n"
[System.IO.File]::WriteAllText((Join-Path $Dest "$name.cue"), $cue, [System.Text.Encoding]::ASCII)
New-Item -ItemType Directory -Force -Path (Join-Path $Dest 'save') | Out-Null

Write-Host ''
Write-Host 'Done. Now copy everything inside the ports folder into roms/ports on your console,'
Write-Host 'restart the console and start SilentHill from Ports.'
Write-Host ''
