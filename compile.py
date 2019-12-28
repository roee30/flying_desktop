import os
import subprocess
from pathlib import Path


def main():
    os.chdir(Path(__file__).parent)
    subprocess.run(
        ["pyinstaller", "--onefile", "--clean", "pyinstaller.spec",]
    )


if __name__ == "__main__":
    main()
