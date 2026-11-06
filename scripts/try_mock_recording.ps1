param(
    [string]$BaseUrl = 'http://localhost:8000',
    [string]$TranscriptPath = (Join-Path $PSScriptRoot '..\fixtures\mock_recording_text\tv_home.txt')
)

$ErrorActionPreference = 'Stop'
$sessionBody = @{
    associate_id = 'test-associate'
    store_id = 'test-store'
    language = 'en'
} | ConvertTo-Json

$session = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/sessions" `
    -ContentType 'application/json' -Body $sessionBody

$recordingBody = @{
    session_id = $session.id
    mock_recording_text = Get-Content -LiteralPath $TranscriptPath -Raw
} | ConvertTo-Json

$reply = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/dev/mock-recordings" `
    -ContentType 'application/json' -Body $recordingBody
$reply | ConvertTo-Json -Depth 10

$history = Invoke-RestMethod -Uri "$BaseUrl/api/v1/sessions/$($session.id)/messages"
$history | ConvertTo-Json -Depth 10
