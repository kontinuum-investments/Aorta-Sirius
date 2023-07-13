rmdir /s /q htmlcov
coverage run -m pytest src/tests
coverage html
htmlcov\index.html