@echo off
echo 🧬 Kurzgesagt AI Assistant - Startup Script
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo ❌ .env file not found!
    echo Please create a .env file with your API keys:
    echo.
    echo OPENAI_API_KEY=your-openai-key-here
    echo PINECONE_API_KEY=your-pinecone-key-here
    echo PINECONE_ENVIRONMENT=gcp-starter
    echo FLASK_SECRET_KEY=your-secret-key-here
    echo.
    pause
    exit /b 1
)

REM Check if requirements are installed
echo 📦 Checking dependencies...
pip list | find "flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Check if data is uploaded
if not exist data\pinecone_data.json (
    echo ⚠️  No data found in Pinecone! 
    echo 📊 Would you like to upload data now? (y/n)
    set /p upload_data=
    if /i "%upload_data%"=="y" (
        echo 📤 Uploading data to Pinecone...
        cd code
        python openai_pinecone_uploader.py
        cd ..
        if %errorlevel% neq 0 (
            echo ❌ Failed to upload data
            pause
            exit /b 1
        )
    )
)

REM Start the application
echo.
echo 🚀 Starting Kurzgesagt AI Assistant...
echo 🌐 The application will open at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py

pause
