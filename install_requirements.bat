@echo off
py -m venv sd_venv
CALL ..\no-budget-bank\sd_venv\Scripts\activate.bat
pip3 install -r requirements.txt