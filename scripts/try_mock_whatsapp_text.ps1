param(
    [string]$BaseUrl = 'http://localhost:8000',
    [string]$TextPath = (Join-Path $PSScriptRoot '..\fixtures\mock_whatsapp_text\tv_question.txt')
)

$ErrorActionPreference = 'Stop'
$sessionBody = @{
    associate_id = 'test-associate'
    store_id = 'test-store'
    language = 'en'
} | ConvertTo-Json

$session = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/sessions" `
    -ContentType 'application/json' -Body $sessionBody

$messageBody = @{
    session_id = $session.id
    sender = '15550100001'
    mock_whatsapp_text = Get-Content -LiteralPath $TextPath -Raw
} | ConvertTo-Json

$reply = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/dev/mock-whatsapp-text" `
    -ContentType 'application/json' -Body $messageBody
$reply | ConvertTo-Json -Depth 15
