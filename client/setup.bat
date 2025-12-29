@echo off
REM OnyxPoker Windows Client Setup Script

echo Setting up OnyxPoker Windows Automation Client...

REM Create virtual environment
python -m venv venv
call venv\Scripts\activate.bat

REM Install dependencies
pip install -r requirements.txt

REM Create configuration file
if not exist .env (
    copy ..\env.example .env
    echo Please edit .env file with your server configuration
)

echo Client setup complete!
echo To run the client:
echo   venv\Scripts\activate.bat
echo   python automation_client.py
