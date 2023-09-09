import os
from typing import List

from setuptools import setup, find_packages


def get_package_name() -> str:
    return "aorta_sirius" if is_production_branch() else "aorta_sirius_dev"


def is_installing() -> bool:
    return os.path.isfile("PKG-INFO")


def get_version() -> str:
    if is_installing():
        with open("PKG-INFO", "r") as package_info_file:
            return package_info_file.read().split("\n")[2].replace("Version: ", "")

    import requests
    from requests import Response

    response: Response = requests.get(f"https://pypi.org/pypi/{get_package_name()}/json")
    assert response.status_code == 200
    version_number: str = response.json()["info"]["version"]
    next_subversion_number: int = int(version_number.split(".")[-1]) + 1
    return ".".join(version_number.split(".")[0:-1], ) + "." + str(next_subversion_number)


def is_production_branch() -> bool:
    return "production" == os.getenv("GITHUB_REF_NAME") or os.path.isdir("src/aorta_sirius.egg-info")


def get_required_packages() -> List[str]:
    requirements_file_path: str = "requirements.txt" if os.path.isfile("requirements.txt") else f"src/{get_package_name()}.egg-info/requires.txt"

    with open(requirements_file_path, "r") as requirements_file:
        return requirements_file.read().split("\n")


setup(
    name=get_package_name(),
    version=get_version(),
    url="https://github.com/kontinuum-investments/Aorta-Sirius",
    author="Kavindu Athaudha",
    author_email="kavindu@kih.com.sg",
    packages=find_packages(where="src", include=["sirius*"]),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=get_required_packages()
)
