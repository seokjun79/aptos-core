# RC2비너스 시작: venus-fx 폴더에서 Claude 원격 세션을 켠다. 바꾸는 것 없음.
$dir = "$HOME\venus-fx"
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
Set-Location $dir
claude --remote-control
