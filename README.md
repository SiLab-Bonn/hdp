# hdp
Highlights der Physik Telescope Readout

This repository contains an eye catching 3d visualization of an ATLAS FE-I4 telescope readout.
Meant to show tracks from the cosmic radiation for educational purposes.

# Requirenments
- pybar software
- MMC3 hardware
- 2 x ATLAS FE-I4

# Setup
Start pybar with two modules that send data to:
- `tcp://127.0.0.1:5678` for bottom module
- `tcp://127.0.0.1:5679` for top module

Steps:
1. Activate Python 2 environment:
  ``` conda activate python2 ```
2. Goto the pybar folder:
  ``` cd ~/git/pyBAR/pybar ```
3. Start the self trigger scan:
  ``` python python scans/scan_fei4_self_trigger.py ```
4. Start the monitor (if not already running):
  Double click on the `Monitor` icon ion the desktop

# Keys:
- `f`: toggle fullscreen
- `x`: toggle sound: off/tracks only/hits and tracks
- `p`: pause
- `r`: delete all tracks and hits
- `space`: add MC track or reset camera in mouse view
- `q e`: move camera down/up
- `a w s d`: move camera in a plane
- `+ -`: accelerate/deaccelerate module rotation
- `l`: toggle legend
- `m`: mouse view (experimental)
