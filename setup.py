from os import path
from setuptools import setup, find_packages
from flying_desktop import __version__

HERE = path.dirname(__file__)

with open(path.join(HERE, "requirements.txt"), "r") as f:
    packages = list(map(str.strip, f))

setup(
    name="flying-desktop",
    version=__version__,
    install_requires=packages,
    packages=find_packages(),
    url="",
    license="",
    author="Roee Nizan",
    author_email="roeen30@gmail.com",
    description="Download wallpapers from your social media accounts",
    entry_points=dict(gui_scripts=["flydesk = flying_desktop.__main__:main"]),
    package_data={"flying_desktop": ["providers/*/credentials.json"]},
)
