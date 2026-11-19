# Venus Sweep Duo EA를 MT5 전략 테스터로 7년 검증 (고객님 Windows 컴퓨터용)
#
# 사용법: PowerShell에 아래 한 줄을 붙여 넣고 Enter (커밋 번호는 비너스가 알려 준 것)
#   [Net.ServicePointManager]::SecurityProtocol = "Tls12"; irm https://raw.githubusercontent.com/seokjun79/aptos-core/<커밋>/trading/run_sweepduo_test.ps1 | iex
#
# 하는 일: EA 내려받기·컴파일 → (MT5를 잠시 닫고) 전략 테스터 2019~현재 실행 → 보고서 분석 → 결과를 클립보드에 복사 → MT5 다시 켜기

# 파이썬·pip이 경고를 stderr로 내도 멈추지 않게 Continue로 두고, 중요한 곳은 직접 검사한다
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# 캐시된 옛 파일을 받지 않도록 커밋 번호로 고정 (비너스가 올릴 때 채움)
$Ref  = "0c4fc753ad3656017a5174c65dd82bfef28ac980"
$Base = "https://raw.githubusercontent.com/seokjun79/aptos-core/$Ref"
$Work = Join-Path $HOME "venus-trading"

function Step([string]$msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Fail([string]$msg) { Write-Host "`n[멈춤] $msg" -ForegroundColor Red; throw $msg }

# ---------------------------------------------------------------- 1
Step "1/7 MT5 찾기"
$DataDir = Join-Path $env:APPDATA "MetaQuotes\Terminal\010E047102812FC0C18890992854220E"
if (-not (Test-Path $DataDir)) {
    $hit = Get-ChildItem "$env:APPDATA\MetaQuotes\Terminal\*\origin.txt" -ErrorAction SilentlyContinue |
           Where-Object { [IO.File]::ReadAllText($_.FullName) -match "IC" } | Select-Object -First 1
    if ($hit) { $DataDir = $hit.DirectoryName }
}
if (-not (Test-Path $DataDir)) { Fail "MT5 데이터 폴더가 없어요: $DataDir" }
$install = ([IO.File]::ReadAllText((Join-Path $DataDir "origin.txt"))).Trim([char]0, ' ', "`r", "`n")
$terminal   = Join-Path $install "terminal64.exe"
$metaeditor = Join-Path $install "metaeditor64.exe"
if (-not (Test-Path $terminal)) { Fail "terminal64.exe를 못 찾았어요: $terminal" }
Write-Host "MT5 설치 폴더: $install"

# ---------------------------------------------------------------- 2
Step "2/7 파일 내려받기"
foreach ($f in @("trading/mt5/VenusSweepDuo.mq5", "trading/backtest/parse_mt5_report.py")) {
    $dest = Join-Path $Work ($f -replace "/", "\")
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Invoke-WebRequest -UseBasicParsing -Uri "$Base/$f" -OutFile $dest -ErrorAction Stop
    Write-Host "  받음: $f"
}

# ---------------------------------------------------------------- 3
Step "3/7 EA 컴파일"
$expDir = Join-Path $DataDir "MQL5\Experts\Venus"
New-Item -ItemType Directory -Force -Path $expDir | Out-Null
Copy-Item (Join-Path $Work "trading\mt5\VenusSweepDuo.mq5") $expDir -Force -ErrorAction Stop
$src = Join-Path $expDir "VenusSweepDuo.mq5"
$ex5 = Join-Path $expDir "VenusSweepDuo.ex5"
$log = Join-Path $expDir "compile_sweepduo.log"
Remove-Item $log, $ex5 -ErrorAction SilentlyContinue
Start-Process -FilePath $metaeditor -ArgumentList "/compile:`"$src`"", "/log:`"$log`"" -Wait
$logText = if (Test-Path $log) { [IO.File]::ReadAllText($log) } else { "" }
if (($logText -match "(\d+)\s+error" -and [int]$Matches[1] -gt 0) -or -not (Test-Path $ex5)) {
    Write-Host $logText
    Fail "EA 컴파일에 실패했어요. 위 내용을 비너스에게 보내 주세요."
}
Write-Host "컴파일 성공: $ex5" -ForegroundColor Green

# ---------------------------------------------------------------- 4
Step "4/7 파이썬 확인"
$py = $null
$direct = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
foreach ($cand in @("python", "py", $direct)) {
    try {
        $v = & $cand --version 2>&1
        if ($LASTEXITCODE -eq 0 -and "$v" -match "Python 3") { $py = $cand; break }
    } catch { }
}
if (-not $py) { Fail "파이썬이 없어요. 먼저 run_backtest.ps1을 한 번 돌려 주세요(자동 설치돼요)." }

# ---------------------------------------------------------------- 5
Step "5/7 전략 테스터 설정"
$to = Get-Date -Format "yyyy.MM.dd"
$ini = Join-Path $DataDir "venus_sweepduo_tester.ini"
@"
[Tester]
Expert=Venus\VenusSweepDuo.ex5
Symbol=EURUSD
Period=M5
Model=1
ExecutionMode=0
Optimization=0
FromDate=2019.01.01
ToDate=$to
ForwardMode=0
Deposit=10000
Currency=USD
Leverage=1:100
Report=Venus_SweepDuo
ReplaceReport=1
ShutdownTerminal=1
Visual=0

[TesterInputs]
InpUseRiskLot=true
InpRiskPct=1.0
InpMaxLots=50
InpPush=false
InpDrawBoxes=false
"@ | Out-File $ini -Encoding unicode   # MT5 설정 파일은 UTF-16(유니코드)으로 저장해야 읽힌다
Write-Host "설정 파일: $ini"
Write-Host "조건: EURUSD 5분봉, 2019.01.01 ~ $to, 1분 OHLC 모델, 시작 잔고 10,000달러, 거래당 위험 1% (R 계산용)"

# ---------------------------------------------------------------- 6
Step "6/7 전략 테스터 실행 (처음엔 과거 데이터를 받느라 10~30분 걸릴 수 있어요)"
$running = Get-Process terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $terminal }
if ($running) {
    Write-Host "전략 테스터를 돌리려면 MT5를 잠시 닫아야 해요. (끝나면 다시 켜 드려요)" -ForegroundColor Yellow
    Write-Host "열려 있는 EA가 실계좌에서 거래 중이면 이 창을 닫고 나중에 하세요." -ForegroundColor Yellow
    Read-Host "괜찮으면 Enter를 누르세요"
    foreach ($p in $running) { [void]$p.CloseMainWindow() }
    for ($i = 0; $i -lt 30 -and (Get-Process terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $terminal }); $i++) {
        Start-Sleep -Seconds 1
    }
    $left = Get-Process terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $terminal }
    if ($left) { Fail "MT5가 닫히지 않았어요. MT5를 직접 닫은 뒤 다시 실행해 주세요." }
}
Get-ChildItem $DataDir -Filter "Venus_SweepDuo*" -ErrorAction SilentlyContinue | Remove-Item -ErrorAction SilentlyContinue
$started = Get-Date
Start-Process -FilePath $terminal -ArgumentList "/config:`"$ini`"" -Wait
$mins = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
$report = Get-ChildItem $DataDir -Filter "Venus_SweepDuo*.htm*" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $report) {
    Start-Process -FilePath $terminal
    Fail "테스트 보고서가 안 만들어졌어요($mins분). MT5 '전략 테스터' 탭의 '일지' 내용을 비너스에게 보내 주세요."
}
Write-Host "테스트 완료 ($mins분): $($report.FullName)" -ForegroundColor Green

# ---------------------------------------------------------------- 7
Step "7/7 결과 분석"
$out = Join-Path $Work "trading\backtest\results\sweepduo_summary.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
Copy-Item $report.FullName (Join-Path (Split-Path $out) $report.Name) -Force
"Venus Sweep Duo 전략 테스터 검증 $(Get-Date -Format 'yyyy-MM-dd HH:mm') (테스트 $mins분)" | Out-File $out -Encoding utf8
$res = & $py (Join-Path $Work "trading\backtest\parse_mt5_report.py") $report.FullName --risk-pct 1.0 2>&1 |
       ForEach-Object { "$_" } | Out-String
$code = $LASTEXITCODE
Write-Host $res
$res | Out-File $out -Append -Encoding utf8
Start-Process -FilePath $terminal   # MT5 다시 켜기
if ($code -ne 0) { Fail "보고서 분석에 실패했어요. 위 내용을 비너스에게 보내 주세요." }

Get-Content $out -Raw | Set-Clipboard
Step "끝!"
Write-Host "결과가 클립보드에 복사됐어요. 비너스와의 대화창에 붙여 넣어 주세요." -ForegroundColor Green
Write-Host "MT5 보고서 원본: $($report.FullName)"
