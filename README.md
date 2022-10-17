# LinSoTracker
<img src="https://linsotracker.com/tracker/gitbanner.png"></img>
## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install LinSoTracker.

```bash
pip install -r requirements.txt
```

## Libraries versions

Here you can find used libraries and their versions

| Library     | Version |
|-------------|---------|
| pygame      | 2.1.2   |
| pygame-menu | 4.2.5   |
| pyinstaller | 5.3     |
| python      | 3.10.0  |

## Build version with no false positive virus

 - Download lastest version of pyinstaller : https://github.com/pyinstaller/pyinstaller/tree/develop
 - Open CMD and go to bootloader directory
 - Run this command :
```bash
    python.exe ./waf all --target-arch=64bit
```
 - Run CMD as admin
 - cd to root Pyinstaller directory
 - Run this command
```bash
    python.exe setup.py install
``` 
 - Go to your LinSoTracker directory and delete "__build__", "__dist__", "__pycache__"
 - Run CMD as admin
```bash
    pyinstaller --clean --onefile --version-file "properties.rc" --icon "icon.ico"  "LinSoTracker.py"
``` 

## Special Thanks

I would like to thank :
 - RawZ
 - Marco
 - Yoshizor 
 - TriRetr0

## Discord 

Join our discord : https://discord.gg/n7AzcMpwXf