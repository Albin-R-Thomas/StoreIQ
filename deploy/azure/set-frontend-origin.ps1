param(
    [Parameter(Mandatory=$true)][string]$Origin,
    [string]$HostName = 'storeiq-api-44d6f926.centralindia.cloudapp.azure.com',
    [string]$IdentityFile = "$env:LOCALAPPDATA\StoreIQ\deployment\id_ed25519"
)
$ErrorActionPreference = 'Stop'
$uri = [Uri]$Origin
if ($uri.Scheme -ne 'https' -or $uri.UserInfo -or $uri.Query -or $uri.Fragment -or $uri.AbsolutePath -ne '/') {
    throw 'Supply an HTTPS origin, such as https://your-project.vercel.app, with no path or query.'
}
$originValue = $uri.GetLeftPart([UriPartial]::Authority)
$encodedOrigin = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($originValue))
$script = @"
set -euo pipefail
exec 9>/opt/storeiq/deployment.lock
flock -n 9
python3 - <<'PY'
import base64, json
from pathlib import Path
origin = base64.b64decode('$encodedOrigin').decode()
path = Path('/opt/storeiq/.env')
lines = [line for line in path.read_text().splitlines() if not line.startswith('PUBLIC_ORIGIN=')]
path.write_text('\n'.join(lines) + '\nPUBLIC_ORIGIN=' + json.dumps(origin) + '\n')
path.chmod(0o600)
PY
cd /opt/storeiq/current
release_dir=`$(readlink -f /opt/storeiq/current)
export STOREIQ_RELEASE=`$(basename "`$release_dir")
docker compose -f compose.azure.yaml up -d --wait --wait-timeout 180
"@
$sshCommand = Join-Path $env:WINDIR 'System32/OpenSSH/ssh.exe'
if (-not (Test-Path $sshCommand)) { $sshCommand = 'ssh' }
$encodedScript = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script.Replace("`r`n", "`n")))
& $sshCommand -i $IdentityFile -o StrictHostKeyChecking=accept-new "azureuser@$HostName" "printf '%s' '$encodedScript' | base64 -d | bash"
if ($LASTEXITCODE -ne 0) { throw 'Frontend origin update failed' }
Write-Output "Allowed frontend origin: $originValue"
