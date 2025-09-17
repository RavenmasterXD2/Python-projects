# PyOS

you will need some libs from PyQt6, QWebEngine, ...

## Guide for correct install

### Requirements

- Windows 10 / 11

- Python 3.11+ -> [Download here](https://www.python.org)
  
⚠️ During install: check “Add Python
to PATH”


### Quick Install (Windows PowerShell)

Open PowerShell and run:
```powershell
Upgrade pip
python -m pip install --upgrade pip
```
Install required dependencies (matching versions)
```powershell
pip install "PyQt6==6.9.*" "PyQt6-WebEngine==6.9.*"
```
That’s it — PyOS will now be ready to run.
(We lock to the 6.9.x series to avoid mismatched version issues.)

## Running PyOS

start PyOS:
(Make sure to start PyOS in its directory) 
example:
```powershell
C:/user/path/Desktop/PyOS> python main.py
```
execute this in powershell:
```powershell
python main.py
```
## Troubleshooting

- WebEngine crashes / GPU errors
  
PyOS already disables GPU via main.py.
If issues persist, set this environment variable:
`
setx QTWEBENGINE_CHROMIUM_FLAGS "--disable-gpu --disable-gpu-compositing --disable-d3d11"
`

- other errors?

either make a issue post or search up the error message. 



