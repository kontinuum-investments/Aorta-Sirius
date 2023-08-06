activate

pytest --cov sirius src/tests --cov-report xml

$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri https://uploader.codecov.io/latest/windows/codecov.exe -Outfile codecov.exe
.\codecov.exe -t $Env:CODECOV_TOKEN

Remove-Item -Path codecov.exe
Remove-Item -Path coverage.xml
