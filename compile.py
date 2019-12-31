"""
Run pyinstaller and create a windows PE (.exe) file
"""
import os
import subprocess
from pathlib import Path


def main():
    os.chdir(Path(__file__).parent)
    subprocess.Popen(
        ["pyinstaller", "--onefile", "--clean", "pyinstaller.spec"]
    ).communicate("y\n".encode())


if __name__ == "__main__":
    main()
