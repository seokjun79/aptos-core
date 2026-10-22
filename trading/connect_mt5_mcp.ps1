# MT5 내장 MCP 서버를 Claude 데스크톱 앱에 연결한다 (고객님 Windows 컴퓨터용)
# 하는 일: Node.js·Claude 데스크톱이 없으면 설치 → API 키 입력받기 → MT5 연결 시험 → Claude 설정 파일에 "mt5" 추가
[Console]::OutputEncoding = [Text.Encoding]::UTF8
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Url = "http://127.0.0.1:22346/mcp"

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}

# 1) Node.js (MCP 다리 역할 프로그램 실행에 필요)
if (-not (Get-Command npx.cmd -ErrorAction SilentlyContinue)) {
    Write-Host "Node.js 설치 중... (1~2분)" -ForegroundColor Yellow
    winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements | Out-Null
    Refresh-Path
}
if (-not (Get-Command npx.cmd -ErrorAction SilentlyContinue)) {
    Write-Host "[멈춤] Node.js 설치를 확인할 수 없어요. 컴퓨터를 다시 켠 뒤 한 번 더 실행해 주세요." -ForegroundColor Red
    return
}

# 2) Claude 데스크톱 앱
$cfgDirs = @()
if (Test-Path (Join-Path $env:APPDATA "Claude")) { $cfgDirs += (Join-Path $env:APPDATA "Claude") }
Get-ChildItem (Join-Path $env:LOCALAPPDATA "Packages") -Filter "Claude_*" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $d = Join-Path $_.FullName "LocalCache\Roaming\Claude"
    if (Test-Path $d) { $cfgDirs += $d }
}
if ($cfgDirs.Count -eq 0) {
    Write-Host "Claude 데스크톱 앱 설치 중... (1~2분)" -ForegroundColor Yellow
    winget install -e --id Anthropic.Claude --accept-package-agreements --accept-source-agreements | Out-Null
    $cfgDirs += (Join-Path $env:APPDATA "Claude")
}

# 3) API 키 (MT5 → 도구 → 옵션 → MCP 탭의 'API 키')
$key = (Read-Host "MT5 옵션 → MCP 탭의 API 키를 붙여 넣고 Enter").Trim()
if ($key -eq "") { Write-Host "[멈춤] API 키가 비어 있어요." -ForegroundColor Red; return }

# 4) MT5 연결 시험 (MT5가 켜져 있고 '내부 서버 활성화'가 체크돼 있어야 함)
$body = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"venus-test","version":"1.0"}}}'
try {
    $r = Invoke-WebRequest -UseBasicParsing -Method Post -Uri $Url -Body $body -TimeoutSec 10 `
        -ContentType "application/json" -Headers @{ Authorization = "Bearer $key"; Accept = "application/json, text/event-stream" }
    Write-Host "MT5 연결 시험 성공 (응답 $($r.StatusCode))" -ForegroundColor Green
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    if ($code -eq 401 -or $code -eq 403) {
        Write-Host "[멈춤] API 키가 맞지 않아요 (응답 $code). MCP 탭에서 키를 다시 복사해 주세요." -ForegroundColor Red; return
    }
    Write-Host "[주의] MT5에 연결하지 못했어요 ($($_.Exception.Message))." -ForegroundColor Yellow
    Write-Host "MT5가 켜져 있는지, 옵션 → MCP 탭에서 '내부 서버 활성화'가 체크돼 있는지 확인해 주세요. 설정은 계속 저장할게요." -ForegroundColor Yellow
}

# 5) Claude 설정 파일에 mt5 추가 (기존 설정은 유지)
$server = [ordered]@{
    command = "cmd"
    args    = @("/c", "npx", "-y", "mcp-remote", $Url, "--allow-http", "--header", 'Authorization:${MT5_AUTH}')
    env     = [ordered]@{ MT5_AUTH = "Bearer $key" }
}
foreach ($dir in $cfgDirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $file = Join-Path $dir "claude_desktop_config.json"
    $cfg = $null
    if (Test-Path $file) {
        Copy-Item $file "$file.bak" -Force
        try { $cfg = Get-Content $file -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $cfg = $null }
    }
    if ($null -eq $cfg) { $cfg = New-Object PSObject }
    if (-not ($cfg.PSObject.Properties.Name -contains "mcpServers")) {
        $cfg | Add-Member -NotePropertyName mcpServers -NotePropertyValue (New-Object PSObject)
    }
    $cfg.mcpServers | Add-Member -NotePropertyName mt5 -NotePropertyValue $server -Force
    [IO.File]::WriteAllText($file, ($cfg | ConvertTo-Json -Depth 10), (New-Object Text.UTF8Encoding($false)))
    Write-Host "저장: $file" -ForegroundColor Green
}

Write-Host ""
Write-Host "끝! Claude 데스크톱 앱을 완전히 껐다가(오른쪽 아래 트레이 아이콘 → 종료) 다시 켜 주세요." -ForegroundColor Green
Write-Host "그다음 Claude에게 'MT5 내 계좌 잔고 알려줘' 라고 물어보면 돼요." -ForegroundColor Green
