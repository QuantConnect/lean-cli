Set-PSDebug -Trace 1

function Fail {
    param( [string]$Message )
    Set-PSDebug -Off
    Write-Error $Message
    exit 1
}

if (-not (Test-Path env:QC_USER_ID) -or -not (Test-Path env:QC_API_TOKEN)) {
    Fail ("These tests require QC_USER_ID and QC_API_TOKEN to be set")
}

mkdir regression-testing
cd regression-testing

lean config set user-id "$env:QC_USER_ID"
lean config set api-token "$env:QC_API_TOKEN"
lean config set default-language python

lean init
