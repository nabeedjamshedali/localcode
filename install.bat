@echo off
:: localcode Windows Installer
:: Run: install.bat

echo.
echo ==========================================
echo   localcode - Local AI Coding Agent
echo   Installing for Windows...
echo ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found

:: Check Ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Ollama not found.
    echo   1. Download from: https://ollama.com/download
    echo   2. Install it
    echo   3. Re-run this installer
    pause
    exit /b 1
)
echo [OK] Ollama found

:: Start Ollama (background)
echo [INFO] Starting Ollama server...
start /b ollama serve
timeout /t 3 /nobreak >nul

:: Pull model
echo [INFO] Pulling qwen2.5-coder:7b model (this takes a few minutes)...
ollama pull qwen2.5-coder:7b
echo [OK] Model ready

:: Create install directory
set INSTALL_DIR=%USERPROFILE%\.localcode
mkdir "%INSTALL_DIR%" 2>nul
xcopy /E /I /Y "%~dp0" "%INSTALL_DIR%\app\" >nul

:: Create launcher
echo @echo off > "%INSTALL_DIR%\localcode.bat"
echo python "%INSTALL_DIR%\app\bin\localcode" %%* >> "%INSTALL_DIR%\localcode.bat"

:: Add to PATH
setx PATH "%INSTALL_DIR%;%PATH%" >nul 2>&1

:: Write config
echo { > "%USERPROFILE%\.localcode\config.json"
echo   "model": "qwen2.5-coder:7b", >> "%USERPROFILE%\.localcode\config.json"
echo   "ollama_url": "http://localhost:11434", >> "%USERPROFILE%\.localcode\config.json"
echo   "auto_confirm": false >> "%USERPROFILE%\.localcode\config.json"
echo } >> "%USERPROFILE%\.localcode\config.json"

echo.
echo ==========================================
echo   SUCCESS! localcode installed!
echo ==========================================
echo.
echo   Restart your terminal, then:
echo   cd your-project
echo   localcode
echo.
pause
