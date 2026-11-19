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
Write-Host "받은 키 길이: $($key.Length)글자 (MT5 키 칸의 글자 수와 같아야 해요)" -ForegroundColor DarkGray
if ($key -eq "") { Write-Host "[멈춤] API 키가 비어 있어요." -ForegroundColor Red; return }

# 4) MT5 연결 시험: 키를 넘기는 방식이 여러 가지라 차례로 시험해서 되는 것을 쓴다
$body = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"venus-test","version":"1.0"}}}'
$tries = @(
    @{ name = "Authorization"; value = "Bearer $key"; url = $Url },
    @{ name = "Authorization"; value = $key;          url = $Url },
    @{ name = "X-API-Key";     value = $key;          url = $Url },
    @{ name = "api-key";       value = $key;          url = $Url },
    @{ name = "";              value = "";            url = "$Url" + "?api_key=" + [Uri]::EscapeDataString($key) },
    @{ name = "";              value = "";            url = "$Url" + "?key=" + [Uri]::EscapeDataString($key) },
    @{ name = "";              value = "";            url = "$Url" + "?token=" + [Uri]::EscapeDataString($key) }
)
$ok = $null; $codes = @()
foreach ($t in $tries) {
    $h = @{ Accept = "application/json, text/event-stream" }
    if ($t.name -ne "") { $h[$t.name] = $t.value }
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Method Post -Uri $t.url -Body $body -TimeoutSec 10 -ContentType "application/json" -Headers $h
        $ok = $t; Write-Host "MT5 연결 시험 성공 (방식: $(if ($t.name) { $t.name } else { '주소에 키' }))" -ForegroundColor Green
        break
    } catch {
        $c = $_.Exception.Response.StatusCode.value__
        if ($null -eq $c) {
            Write-Host "[멈춤] MT5에 닿지 않아요 ($($_.Exception.Message))." -ForegroundColor Red
            Write-Host "MT5가 켜져 있는지, 옵션 → MCP 탭 '내부 서버 활성화' 체크 후 '확인'을 눌렀는지 봐 주세요." -ForegroundColor Red
            return
        }
        $codes += $c
        if ($codes.Count -eq 1) {
            # 첫 거절 때 MT5가 보낸 설명을 보여 준다 (원인 파악용)
            try {
                $resp = $_.Exception.Response
                $wa = $resp.Headers["WWW-Authenticate"]
                $txt = (New-Object IO.StreamReader($resp.GetResponseStream())).ReadToEnd()
                Write-Host "MT5 답변: $wa $txt" -ForegroundColor DarkGray
            } catch {}
        }
    }
}
if ($null -eq $ok) {
    Write-Host "[멈춤] 모든 방식에서 키를 받아 주지 않았어요 (응답 $($codes -join ','))." -ForegroundColor Red
    Write-Host "MT5 옵션 → MCP 탭에서 '생성하다'를 누른 뒤 반드시 '확인'을 눌러 저장하고, 그 키로 다시 해 주세요." -ForegroundColor Red
    return
}

# 5) Claude 설정 파일에 mt5 추가 (기존 설정은 유지)
if ($ok.name -ne "") {
    $server = [ordered]@{
        command = "cmd"
        args    = @("/c", "npx", "-y", "mcp-remote", $ok.url, "--allow-http", "--header", ($ok.name + ':${MT5_AUTH}'))
        env     = [ordered]@{ MT5_AUTH = $ok.value }
    }
} else {
    $server = [ordered]@{
        command = "cmd"
        args    = @("/c", "npx", "-y", "mcp-remote", $ok.url, "--allow-http")
    }
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
