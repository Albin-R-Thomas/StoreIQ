param(
    [string]$HostName = 'storeiq-api-44d6f926.centralindia.cloudapp.azure.com',
    [string]$IdentityFile = "$env:LOCALAPPDATA\StoreIQ\deployment\id_ed25519",
    [string]$EnvironmentFile
)
$ErrorActionPreference = 'Stop'
$repository = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$revision = & git -C $repository rev-parse --short=12 HEAD
if ($LASTEXITCODE -ne 0) { throw 'Cannot determine source revision' }
$release = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '-' + $revision.Trim()
$archive = Join-Path $env:TEMP "storeiq-$release.tar.gz"
$remote = "azureuser@$HostName"
$sshCommand = Join-Path $env:WINDIR 'System32/OpenSSH/ssh.exe'
$scpCommand = Join-Path $env:WINDIR 'System32/OpenSSH/scp.exe'
if (-not (Test-Path $sshCommand)) { $sshCommand = 'ssh' }
if (-not (Test-Path $scpCommand)) { $scpCommand = 'scp' }
$sshArguments = @('-i', $IdentityFile, '-o', 'StrictHostKeyChecking=accept-new', '-o', 'ConnectTimeout=15')
function Assert-Exit([string]$Operation) {
    if ($LASTEXITCODE -ne 0) { throw "$Operation failed (exit $LASTEXITCODE)" }
}
$tarCommand = Join-Path $env:WINDIR 'System32/tar.exe'
if (-not (Test-Path $tarCommand)) { $tarCommand = 'tar' }
& $tarCommand -czf $archive --exclude=__pycache__ --exclude=frontend/node_modules --exclude=frontend/dist --exclude=frontend/.env* --exclude=*.tsbuildinfo -C $repository Dockerfile Dockerfile.backend compose.azure.yaml pyproject.toml .dockerignore alembic.ini app migrations fixtures frontend deploy/azure
Assert-Exit 'Source packaging'
if ($EnvironmentFile) {
    & $sshCommand @sshArguments $remote 'umask 077; touch /opt/storeiq/.env.incoming; chmod 600 /opt/storeiq/.env.incoming'
    Assert-Exit 'Environment preparation'
    & $scpCommand @sshArguments $EnvironmentFile "${remote}:/opt/storeiq/.env.incoming"
    Assert-Exit 'Environment upload'
    & $sshCommand @sshArguments $remote 'mv /opt/storeiq/.env.incoming /opt/storeiq/.env'
    Assert-Exit 'Environment installation'
}
& $sshCommand @sshArguments $remote "mkdir -p /opt/storeiq/releases/$release"
Assert-Exit 'Release directory creation'
& $scpCommand @sshArguments $archive "${remote}:/opt/storeiq/releases/$release/source.tar.gz"
Assert-Exit 'Source upload'
& $sshCommand @sshArguments $remote "tar -xzf /opt/storeiq/releases/$release/source.tar.gz -C /opt/storeiq/releases/$release && bash /opt/storeiq/releases/$release/deploy/azure/release.sh /opt/storeiq/releases/$release $release"
Assert-Exit 'Website deployment'
Remove-Item -LiteralPath $archive
Write-Output "Website release $release deployed to https://$HostName"
