# 使用 Nuitka 构建 Windows x64 单文件程序，并提取目标程序图标。

[CmdletBinding()]
param(
    # 默认执行完整构建；传入 -Clean 可先删除旧的构建缓存。
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetExecutable = "D:\天龙八部\Launch.exe"
$assetDirectory = Join-Path $projectRoot "assets"
$iconPath = Join-Path $assetDirectory "app.ico"
$buildDirectory = Join-Path $projectRoot "build"
$distDirectory = Join-Path $projectRoot "dist"
$outputExecutable = Join-Path $distDirectory "KeyboardScript.exe"
$compilerIncludeDirectory = "C:\Nuitka-Mingw-Include"

function Stop-WithError([string]$message) {
    # 统一输出构建错误并立即结束脚本，避免继续生成不完整的发布物。
    Write-Error $message
    exit 1
}

function Ensure-Command([string]$commandName) {
    # 在执行构建前确认基础命令存在，错误信息比后续调用失败更明确。
    if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        Stop-WithError "找不到命令：$commandName。请先安装 Python 3.12 和 Nuitka。"
    }
}

function Export-TargetIcon([string]$sourcePath, [string]$destinationPath) {
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        Stop-WithError "目标程序不存在，无法提取图标：$sourcePath"
    }

    New-Item -ItemType Directory -Path (Split-Path -Parent $destinationPath) -Force | Out-Null
    Add-Type -AssemblyName System.Drawing
    $sourceIcon = $null
    $outputStream = $null
    try {
        $sourceIcon = [System.Drawing.Icon]::ExtractAssociatedIcon($sourcePath)
        if ($null -eq $sourceIcon) {
            Stop-WithError "目标程序没有可提取的关联图标：$sourcePath"
        }
        $outputStream = [System.IO.File]::Open($destinationPath, [System.IO.FileMode]::Create)
        $sourceIcon.Save($outputStream)
    } catch {
        Stop-WithError "提取目标程序图标失败：$($_.Exception.Message)"
    } finally {
        if ($null -ne $outputStream) { $outputStream.Dispose() }
        if ($null -ne $sourceIcon) { $sourceIcon.Dispose() }
    }
    if (-not (Test-Path -LiteralPath $destinationPath -PathType Leaf)) {
        Stop-WithError "图标提取后未生成文件：$destinationPath"
    }
}

function Prepare-CompilerHeaders() {
    # 当前环境的 Nuitka 缓存路径较长，部分 MinGW 头文件会因此无法互相包含。
    $cacheCandidates = @(
        (Join-Path $env:LOCALAPPDATA "Nuitka\Nuitka\Cache\downloads\gcc")
    )
    $packagesDirectory = Join-Path $env:LOCALAPPDATA "Packages"
    if (Test-Path -LiteralPath $packagesDirectory) {
        $cacheCandidates += Get-ChildItem -LiteralPath $packagesDirectory -Directory -Filter "OpenAI.Codex*" |
            ForEach-Object { Join-Path $_.FullName "LocalCache\Local\Nuitka\Nuitka\Cache\downloads\gcc" }
    }
    $nuitkaCache = $cacheCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($nuitkaCache)) {
        # 已安装完整编译器时不需要额外设置头文件路径。
        return
    }
    $includeSource = Get-ChildItem -LiteralPath $nuitkaCache -Directory -Recurse -ErrorAction SilentlyContinue |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "x86_64-w64-mingw32\include\windows.h") } |
        Select-Object -First 1
    if ($null -eq $includeSource) {
        # Nuitka 尚未下载 MinGW 时，后续 Nuitka 命令会负责下载它。
        return
    }
    $sourcePath = Join-Path $includeSource.FullName "x86_64-w64-mingw32\include"
    if (-not (Test-Path -LiteralPath (Join-Path $compilerIncludeDirectory "sdkddkver.h"))) {
        New-Item -ItemType Directory -Path $compilerIncludeDirectory -Force | Out-Null
        Copy-Item -Path (Join-Path $sourcePath "*") -Destination $compilerIncludeDirectory -Recurse -Force
    }
    $env:CPATH = $compilerIncludeDirectory
}

Ensure-Command "python"
if ($Clean) {
    Remove-Item -LiteralPath $buildDirectory -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $distDirectory -Recurse -Force -ErrorAction SilentlyContinue
}

Export-TargetIcon $targetExecutable $iconPath
# 使用模块探测代替 pip show，避免 PowerShell 把“未安装”的提示当成异常。
python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('nuitka') else 1)" 2> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "正在安装 Nuitka..."
    python -m pip install "Nuitka>=2.7,<3"
    if ($LASTEXITCODE -ne 0) { Stop-WithError "Nuitka 安装失败。" }
}

Prepare-CompilerHeaders
New-Item -ItemType Directory -Path $distDirectory -Force | Out-Null
$nuitkaArguments = @(
    "-m", "nuitka",
    "--mode=onefile",
    "--enable-plugin=pyside6",
    "--windows-console-mode=disable",
    "--lto=yes",
    "--assume-yes-for-downloads",
    "--jobs=$([Math]::Max(1, [Environment]::ProcessorCount - 1))",
    "--remove-output",
    "--output-dir=$distDirectory",
    "--output-filename=KeyboardScript.exe",
    "--windows-icon-from-ico=$iconPath",
    "--include-data-files=$iconPath=assets/app.ico",
    "app.py"
)
Push-Location $projectRoot
try {
    python @nuitkaArguments
    if ($LASTEXITCODE -ne 0) { Stop-WithError "Nuitka 构建失败。" }
} finally {
    Pop-Location
}

Copy-Item -LiteralPath (Join-Path $projectRoot "config.toml") -Destination $distDirectory -Force
if (-not (Test-Path -LiteralPath $outputExecutable -PathType Leaf)) {
    Stop-WithError "构建完成但未找到输出文件：$outputExecutable"
}

$sizeMiB = [math]::Round((Get-Item -LiteralPath $outputExecutable).Length / 1MB, 2)
Write-Host "构建完成：$outputExecutable ($sizeMiB MiB)"
Write-Host "发布目录同时包含：$distDirectory\config.toml"
