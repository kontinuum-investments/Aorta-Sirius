import datetime
import sys

from setuptools import setup, find_packages

# TODO: Figure out the versioning system
setup(
    name="aorta_sirius",
    version="0.0.4",
    url="https://github.com/kontinuum-investments/Aorta-Sirius",
    author="Kavindu Athaudha",
    author_email="kavindu@kih.com.sg",
    packages=find_packages(where="src", include=["sirius*"]),
    package_dir={"": "src"},
    install_requires=[]
)
