# Venus 백테스트 한 번에 돌리기 (고객님 Windows 컴퓨터용)
#
# 사용법: MT5를 켜고 IC마켓 계좌에 로그인한 상태에서, PowerShell에 아래 한 줄을 붙여 넣고 Enter
#   [Net.ServicePointManager]::SecurityProtocol = "Tls12"; irm https://raw.githubusercontent.com/seokjun79/aptos-core/claude/master-agent-system-o87ntp/trading/run_backtest.ps1 | iex
#
# 하는 일: 파일 내려받기 → EA 컴파일 → MT5에서 가격 데이터 꺼내기 → 모델 A·B 백테스트 → 결과를 클립보드에 복사

# 파이썬·pip이 경고를 stderr로 내도 멈추지 않게 Continue로 두고, 중요한 곳은 직접 검사한다
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
# 고객님이 알려 준 IC마켓 MT5 데이터 폴더. 없으면 origin.txt에 IC가 들어간 폴더를 찾는다.
$DataDir = Join-Path $env:APPDATA "MetaQuotes\Terminal\010E047102812FC0C18890992854220E"
if (-not (Test-Path $DataDir)) {
    $hit = Get-ChildItem "$env:APPDATA\MetaQuotes\Terminal\*\origin.txt" -ErrorAction SilentlyContinue |
           Where-Object { [IO.File]::ReadAllText($_.FullName) -match "IC" } | Select-Object -First 1
    if ($hit) { $DataDir = $hit.DirectoryName }
}
$Branch  = "claude/master-agent-system-o87ntp"
$Base    = "https://raw.githubusercontent.com/seokjun79/aptos-core/$Branch"
$Work    = Join-Path $HOME "venus-trading"

function Step([string]$msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Fail([string]$msg) { Write-Host "`n[멈춤] $msg" -ForegroundColor Red; throw $msg }

# ---------------------------------------------------------------- 1
Step "1/6 MT5 찾기"
if (-not (Test-Path $DataDir)) { Fail "MT5 데이터 폴더가 없어요: $DataDir" }
$install = $null
$origin = Join-Path $DataDir "origin.txt"
if (Test-Path $origin) {
    $install = ([IO.File]::ReadAllText($origin)).Trim([char]0, ' ', "`r", "`n")
}
if (-not $install -or -not (Test-Path (Join-Path $install "terminal64.exe"))) {
    $found = Get-ChildItem "C:\Program Files*\*\terminal64.exe" -ErrorAction SilentlyContinue |
             Where-Object { $_.DirectoryName -match "IC" } | Select-Object -First 1
    if (-not $found) { Fail "terminal64.exe를 못 찾았어요. MT5 설치 폴더를 알려 주세요." }
    $install = $found.DirectoryName
}
$terminal   = Join-Path $install "terminal64.exe"
$metaeditor = Join-Path $install "metaeditor64.exe"
Write-Host "MT5 설치 폴더: $install"

# ---------------------------------------------------------------- 2
Step "2/6 Venus 파일 내려받기"
$files = @(
    "trading/mt5/VenusModelV1.mq5",
    "trading/mt5/export_data.py",
    "trading/backtest/venus_backtest.py",
    "trading/strategy/venus_model_v1.md"
)
foreach ($f in $files) {
    $dest = Join-Path $Work ($f -replace "/", "\")
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Invoke-WebRequest -UseBasicParsing -Uri "$Base/$f" -OutFile $dest -ErrorAction Stop
    Write-Host "  받음: $f"
}

# ---------------------------------------------------------------- 3
Step "3/6 EA 컴파일"
$expDir = Join-Path $DataDir "MQL5\Experts\Venus"
New-Item -ItemType Directory -Force -Path $expDir | Out-Null
Copy-Item (Join-Path $Work "trading\mt5\VenusModelV1.mq5") $expDir -Force -ErrorAction Stop
$src = Join-Path $expDir "VenusModelV1.mq5"
$log = Join-Path $expDir "compile.log"
Remove-Item $log -ErrorAction SilentlyContinue
Remove-Item (Join-Path $expDir "VenusModelV1.ex5") -ErrorAction SilentlyContinue
Start-Process -FilePath $metaeditor -ArgumentList "/compile:`"$src`"", "/log:`"$log`"" -Wait
$logText = if (Test-Path $log) { [IO.File]::ReadAllText($log) } else { "" }
$ex5 = Join-Path $expDir "VenusModelV1.ex5"
if ($logText -match "(\d+)\s+error" -and [int]$Matches[1] -gt 0) {
    Write-Host $logText
    Fail "EA 컴파일 오류가 있어요. 위 내용을 비너스에게 보내 주세요."
}
if (-not (Test-Path $ex5)) {
    Write-Host $logText
    Fail "컴파일된 파일(VenusModelV1.ex5)이 안 생겼어요. 위 내용을 비너스에게 보내 주세요."
}
Write-Host "컴파일 성공: $ex5" -ForegroundColor Green

# ---------------------------------------------------------------- 4
Step "4/6 파이썬 준비"
$py = $null
foreach ($cand in @("python", "py")) {
    try {
        $v = & $cand --version 2>&1
        if ($LASTEXITCODE -eq 0 -and "$v" -match "Python 3") { $py = $cand; break }
    } catch { }
}
if (-not $py -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "파이썬이 없어서 자동으로 설치할게요 (1~3분)..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
    # 새로 설치된 파이썬을 이 창에서 바로 쓸 수 있게 PATH를 다시 읽는다
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
    $direct = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
    foreach ($cand in @($direct, "python", "py")) {
        try {
            $v = & $cand --version 2>&1
            if ($LASTEXITCODE -eq 0 -and "$v" -match "Python 3") { $py = $cand; break }
        } catch { }
    }
}
if (-not $py) {
    Fail "파이썬이 없어요. https://www.python.org/downloads/ 에서 설치할 때 'Add python.exe to PATH'에 꼭 체크하고, PowerShell을 새로 연 뒤 다시 실행해 주세요."
}
& $py -m pip install --quiet --disable-pip-version-check MetaTrader5 pandas numpy matplotlib
if ($LASTEXITCODE -ne 0) { Fail "파이썬 패키지 설치에 실패했어요." }
Write-Host "파이썬 준비 완료 ($py)"

# ---------------------------------------------------------------- 5
Step "5/6 MT5에서 EURUSD 가격 데이터 꺼내기 (몇 분 걸려요)"
$env:MT5_PATH = $terminal
& $py (Join-Path $Work "trading\mt5\export_data.py") 2019-01-01
if ($LASTEXITCODE -ne 0) { Fail "데이터를 못 꺼냈어요. MT5가 켜져 있고 로그인돼 있는지 확인해 주세요." }
$csv = Join-Path $Work "trading\data\EURUSD_M15_icmarkets.csv"
if (-not (Test-Path $csv)) { Fail "M15 데이터 파일이 안 생겼어요: $csv" }

# ---------------------------------------------------------------- 6
Step "6/6 백테스트 (모델 A 모멘텀, 모델 B CRT)"
$bt  = Join-Path $Work "trading\backtest\venus_backtest.py"
$out = Join-Path $Work "trading\backtest\results\summary.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
"Venus 백테스트 결과 $(Get-Date -Format 'yyyy-MM-dd HH:mm')" | Out-File $out -Encoding utf8
Get-Content (Join-Path $Work "trading\data\account_symbol_info.txt") -Encoding UTF8 -ErrorAction SilentlyContinue |
    Out-File $out -Append -Encoding utf8
foreach ($m in @("A", "B")) {
    "`n########## 모델 $m ##########" | Out-File $out -Append -Encoding utf8
    $res = & $py $bt --data $csv --model $m --grid 2>&1 | ForEach-Object { "$_" } | Out-String
    $code = $LASTEXITCODE
    Write-Host $res
    $res | Out-File $out -Append -Encoding utf8
    if ($code -ne 0) { Fail "모델 $m 백테스트가 실패했어요. 위 내용을 비너스에게 보내 주세요." }
}

Get-Content $out -Raw | Set-Clipboard
Step "끝!"
Write-Host "결과 요약이 클립보드에 복사됐어요. 비너스와의 대화창에 그대로 붙여 넣어 주세요." -ForegroundColor Green
Write-Host "결과 파일과 그래프 폴더: $(Split-Path $out)"
