import os
from typing import List

import requests
from requests import Response
from setuptools import setup, find_packages


def get_package_name() -> str:
    return "aorta_sirius" if is_production_branch() else "aorta_sirius_dev"


def get_next_version() -> str:
    response: Response = requests.get(f"https://pypi.org/pypi/{get_package_name()}/json")
    assert response.status_code == 200
    version_number: str = response.json()["info"]["version"]
    next_subversion_number: int = int(version_number.split(".")[-1]) + 1
    return ".".join(version_number.split(".")[0:-1], ) + "." + str(next_subversion_number)


def is_production_branch() -> bool:
    return "production" == os.getenv("GITHUB_REF_NAME")


def get_required_packages() -> List[str]:
    with open("requirements.txt", "r") as requirements_file:
        return requirements_file.read().split("\n")


setup(
    name=get_package_name(),
    version=get_next_version(),
    url="https://github.com/kontinuum-investments/Aorta-Sirius",
    author="Kavindu Athaudha",
    author_email="kavindu@kih.com.sg",
    packages=find_packages(where="src", include=["sirius*"]),
    package_dir={"": "src"},
    install_requires=get_required_packages()
)
