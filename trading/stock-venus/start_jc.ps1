# JC비너스 시작 스크립트: 증권 연결 서버(Docker)가 준비된 뒤에 Claude를 켠다.
# PC가 켜지자마자 Claude가 먼저 켜지면 kis-trade/tossinvest 연결이 실패하던 문제를 막는다.
# 바꾸는 것 없음: 포트가 열렸는지 확인만 하고 기다린다(최대 10분).

$ports = @(3000, 8000)
$deadline = (Get-Date).AddMinutes(10)

Write-Host "증권 연결 서버를 기다리는 중... (포트 $($ports -join ', '))"
while ((Get-Date) -lt $deadline) {
    $ready = $true
    foreach ($p in $ports) {
        $ok = Test-NetConnection -ComputerName 127.0.0.1 -Port $p -InformationLevel Quiet -WarningAction SilentlyContinue
        if (-not $ok) { $ready = $false; break }
    }
    if ($ready) { break }
    Start-Sleep -Seconds 10
}

if ($ready) {
    Write-Host "준비됨. 20초 더 기다린 뒤 JC비너스를 켭니다."
    Start-Sleep -Seconds 20
} else {
    Write-Host "10분 기다려도 서버가 안 떠서 그냥 켭니다. 켜진 뒤 /mcp 로 다시 연결하세요."
}

Set-Location "$HOME\stock-venus"
claude --remote-control
