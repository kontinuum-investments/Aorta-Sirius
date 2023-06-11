import datetime
import sys

import requests
from requests import Response
from setuptools import setup, find_packages


def get_next_version() -> str:
    response: Response = requests.get("https://pypi.org/pypi/aorta-sirius/json")
    assert response.status_code == 200
    version_number: str = response.json()["info"]["version"]
    next_subversion_number: int = int(version_number.split(".")[-1]) + 1
    return ".".join(version_number.split(".")[0:-1], ) + "." + str(next_subversion_number)


setup(
    name="aorta_sirius",
    version=get_next_version(),
    url="https://github.com/kontinuum-investments/Aorta-Sirius",
    author="Kavindu Athaudha",
    author_email="kavindu@kih.com.sg",
    packages=find_packages(where="src", include=["sirius*"]),
    package_dir={"": "src"},
    install_requires=[]
)
