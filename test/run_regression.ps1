$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
$playbackTest = Join-Path $PSScriptRoot "playback.test.mjs"

Push-Location $repositoryRoot

try {
    & $python -m unittest discover -s test -p "test_*.py" -v

    if ($LASTEXITCODE -ne 0) {
        throw "Python regression tests failed."
    }

    & node --experimental-default-type=module --test $playbackTest

    if ($LASTEXITCODE -ne 0) {
        throw "JavaScript regression tests failed."
    }
}
finally {
    Pop-Location
}
