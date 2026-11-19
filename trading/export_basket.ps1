# 7종목 가격 데이터를 바탕화면 venus_data.zip으로 꺼낸다 (고객님 Windows 컴퓨터용, MT5를 켜고 로그인한 상태에서)
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Ref = "80df06d468447c683a26aa8063007b138e82ac02"
$DataDir = Join-Path $env:APPDATA "MetaQuotes\Terminal\010E047102812FC0C18890992854220E"
$install = ([IO.File]::ReadAllText((Join-Path $DataDir "origin.txt"))).Trim([char]0, ' ', "`r", "`n")
$env:MT5_PATH = Join-Path $install "terminal64.exe"
$py = $null
foreach ($cand in @("python", "py", (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"))) {
    try { $v = & $cand --version 2>&1; if ($LASTEXITCODE -eq 0 -and "$v" -match "Python 3") { $py = $cand; break } } catch { }
}
if (-not $py) { Write-Host "[멈춤] 파이썬이 없어요." -ForegroundColor Red; return }
& $py -m pip install --quiet --disable-pip-version-check MetaTrader5 pandas
$script = Join-Path $env:TEMP "export_basket.py"
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/seokjun79/aptos-core/$Ref/trading/mt5/export_basket.py" -OutFile $script -ErrorAction Stop
Write-Host "7종목 데이터를 꺼내는 중이에요 (몇 분 걸려요)..." -ForegroundColor Yellow
& $py $script 2019-01-01
$zip = Join-Path ([Environment]::GetFolderPath("Desktop")) "venus_data.zip"
if (Test-Path $zip) {
    Write-Host "완성! 바탕화면의 venus_data.zip 파일을 비너스 대화창에 끌어다 놓아 주세요." -ForegroundColor Green
    explorer.exe /select,"$zip"
} else {
    Write-Host "[멈춤] 파일이 안 만들어졌어요. 위 내용을 비너스에게 보내 주세요." -ForegroundColor Red
}
