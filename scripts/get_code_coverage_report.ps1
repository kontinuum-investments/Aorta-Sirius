activate

Remove-Item -LiteralPath "htmlcov" -Force -Recurse
pytest --cov sirius src/tests --cov-report html
start msedge /htmlcov/index.html