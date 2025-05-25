# treadmill-remote-bertec-fit5

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-≥3.8-blue.svg)](https://www.python.org/)
[![GitHub Repo](https://img.shields.io/badge/Source-GitHub-black?logo=github)](https://github.com/thomasaout/treadmill-remote-bertec-fit5)
[![Cite this](https://img.shields.io/badge/Cite%20this-APA-lightgrey.svg)](https://github.com/thomasaout/treadmill-remote-bertec-fit5/blob/main/CITATION.cff)

Python tool to control a Bertec Fit 5 treadmill remotely via socket and GUI.


# treadmill-remote-bertec-fit5

Python tool to control a Bertec Fit 5 treadmill remotely via socket and GUI.

## 📝 Description

This project provides a set of Python scripts to remotely control a Bertec Fit 5 instrumented treadmill through socket communication and a user-friendly graphical interface.

## 📂 Contents

- `BertecRemoteControl.py`: API for Bertec treadmill control
- `interface.py`: Functions for managing UI events and user interaction
- `treadmill_remote.py`: Main GUI handling socket communication with the treadmill
- `python_client_demo.py`: Sample client for testing socket-based remote control
- `config.json`: Stores GUI layout parameters (button positions and window size)

## ▶️ Getting Started

### Requirements

- Python ≥ 3.8
- PyQt5
- Standard libraries: `socket`, `json`

### Run the interface

To launch the GUI, run: 

```bash
python treadmill_remote.py
