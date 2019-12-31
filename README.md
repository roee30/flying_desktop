# Flying Desktop
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

It's a desktop in the cloud!

## Functionality
Downloads photos from your personal Facebook and Google libraries and sets them as your wallpaper.

## Purpose
This is a POC for combining asynchronous code of two types: `asyncio` and `tkinter`.
The main "trick" is having a thread run the `asyncio` loop and the main thread running the `tkinter` loop.

## Installation & Running
### Direct Download
1. Download `flydesk.exe` executable from the [releases](http://github.com/roee30/flying_desktop/releases/latest) page
2. Run the executable

### With pip
```
pip install .
flydesk
```

### With pyinstaller
In order to run the (experimental) [`pyinstaller`](https://github.com/pyinstaller/pyinstaller) build for Windows, run:
```
pip install .
python compile.py
dist\flydesk
```
## Usage
1. Press "Connect"
2. Log in to Facebook and/or Google 
3. Press "OK"
4. Press "Hit me"

## Todo
- [x] add periodic wallpaper switching
- [ ] add Linux binary packaging

## Similar applications

- [Photo Screen Saver](https://chrome.google.com/webstore/detail/photo-screen-saver/kohpcmlfdjfdggcjmjhhbcbankgmppgc)
