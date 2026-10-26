# Venus CRT 비서 EA을 MT5에 설치하고 컴파일한다 (고객님 Windows 컴퓨터용)
[Console]::OutputEncoding = [Text.Encoding]::UTF8
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Ref = "96ace7e54047becdee5d65fe284152b7d0457bf0"
$DataDir = Join-Path $env:APPDATA "MetaQuotes\Terminal\010E047102812FC0C18890992854220E"
$install = ([IO.File]::ReadAllText((Join-Path $DataDir "origin.txt"))).Trim([char]0, ' ', "`r", "`n")
$expDir = Join-Path $DataDir "MQL5\Experts\Venus"
New-Item -ItemType Directory -Force -Path $expDir | Out-Null
$src = Join-Path $expDir "VenusCRTAssistant.mq5"
$ex5 = Join-Path $expDir "VenusCRTAssistant.ex5"
$log = Join-Path $expDir "compile_crt_assistant.log"
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/seokjun79/aptos-core/$Ref/trading/mt5/VenusCRTAssistant.mq5" -OutFile $src -ErrorAction Stop
Remove-Item $log, $ex5 -ErrorAction SilentlyContinue
Start-Process -FilePath (Join-Path $install "metaeditor64.exe") -ArgumentList "/compile:`"$src`"", "/log:`"$log`"" -Wait
$logText = if (Test-Path $log) { [IO.File]::ReadAllText($log) } else { "" }
if (($logText -match "(\d+)\s+error" -and [int]$Matches[1] -gt 0) -or -not (Test-Path $ex5)) {
    Write-Host $logText
    Write-Host "[멈춤] 컴파일 오류예요. 위 내용을 비너스에게 보내 주세요." -ForegroundColor Red
} else {
    Write-Host "설치·컴파일 성공! Venus\VenusCRTAssistant.ex5 (v1.52)" -ForegroundColor Green
}
