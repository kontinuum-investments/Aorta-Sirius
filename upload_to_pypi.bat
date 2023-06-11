del /S /Q dist\*
del /S /Q src\aorta_sirius.egg-info
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python setup.py sdist
venv\Scripts\twine upload -u __token__ -p %PYPI_API_TOKEN% dist\*