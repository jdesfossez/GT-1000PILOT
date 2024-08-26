#!/bin/bash

pyinstaller  -n GT-1000PILOT --collect-all pygt1000 --collect-all gt1000pilot --clean --onefile launch.py
