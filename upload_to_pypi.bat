venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python setup.py sdist %datetimef%
venv\Scripts\twine upload -u __token__ -p %PYPI_API_TOKEN% dist\*