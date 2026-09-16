[CmdletBinding()]
param([string]$Destination = "artifacts/astracore-sources")

$ErrorActionPreference = "Stop"
$repositoryRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$destinationRoot = [IO.Path]::GetFullPath((Join-Path $repositoryRoot $Destination))

function Get-PinnedSource([string]$Name, [string]$Repository, [string]$Commit, [string]$FallbackRepository = "") {
    $directory = Join-Path $destinationRoot $Name
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null
        $cloned = $false
        try {
            & git clone --filter=blob:none $Repository $directory
            if ($LASTEXITCODE -eq 0) { $cloned = $true }
        } catch { }
        if (-not $cloned -and -not [string]::IsNullOrWhiteSpace($FallbackRepository)) {
            Write-Host "Primary clone failed for $Name, attempting fallback mirror $FallbackRepository..." -ForegroundColor Yellow
            if (Test-Path -LiteralPath $directory) { Remove-Item -LiteralPath $directory -Recurse -Force }
            & git clone --filter=blob:none $FallbackRepository $directory
            if ($LASTEXITCODE -eq 0) { $cloned = $true }
        }
        if (-not $cloned) { throw "Failed to clone $Name from $Repository." }
    }
    & git -C $directory fetch --depth 1 origin $Commit
    if ($LASTEXITCODE -ne 0) { throw "Failed to fetch pinned commit $Commit for $Name." }
    & git -C $directory checkout --detach $Commit
    if ($LASTEXITCODE -ne 0) { throw "Failed to checkout pinned commit $Commit for $Name." }
    $actual = (& git -C $directory rev-parse HEAD).Trim()
    if ($actual -ne $Commit) { throw "$Name commit mismatch: actual $actual != expected $Commit" }
    Write-Host "==> $Name pinned to $actual" -ForegroundColor Green
}

Get-PinnedSource "ffmpeg" "https://github.com/FFmpeg/FFmpeg.git" "bf1b838f2ab88b4f8fd83443325c782ea0e0f7fa" "https://git.ffmpeg.org/ffmpeg.git"
Get-PinnedSource "mpv" "https://github.com/mpv-player/mpv.git" "41f6a645068483470267271e1d09966ca3b9f413"
Get-PinnedSource "libass" "https://github.com/libass/libass.git" "4a05d8127f525943ebf45fdc6497c9e665947f0d"
Get-PinnedSource "libplacebo" "https://code.videolan.org/videolan/libplacebo.git" "cee9b076f2c63104ccfd497fa79c39a867293ec4" "https://github.com/haasn/libplacebo.git"
Get-PinnedSource "x265" "https://bitbucket.org/multicoreware/x265_git.git" "e444744c03978c1fb4e037168967020cf2648427" "https://github.com/videolan/x265.git"
Get-PinnedSource "harfbuzz" "https://github.com/harfbuzz/harfbuzz.git" "36cb489cb02ce4b92099669ba9f9bea348eff93f"
Get-PinnedSource "dav1d" "https://code.videolan.org/videolan/dav1d.git" "54706fc6bc0cdecab7e9593974a4039cc038fca7" "https://github.com/videolan/dav1d.git"

Write-Host "==> All pinned source trees prepared in $destinationRoot" -ForegroundColor Green
