@echo off
REM Build Lambda Deployment Package Script (Windows)
REM This script creates a deployment package for AWS Lambda

echo =========================================
echo Building Lambda Deployment Package
echo =========================================

REM Configuration
set PACKAGE_DIR=lambda_package
set ZIP_FILE=ecommerce-etl-lambda.zip

REM Clean up previous builds
echo Cleaning up previous builds...
if exist %PACKAGE_DIR% rmdir /s /q %PACKAGE_DIR%
if exist %ZIP_FILE% del /q %ZIP_FILE%

REM Create package directory
echo Creating package directory...
mkdir %PACKAGE_DIR%

REM Install dependencies
echo Installing Python dependencies...
pip install -r ..\requirements.txt -t %PACKAGE_DIR%

REM Copy source code
echo Copying source code...
xcopy /E /I /Y ..\src %PACKAGE_DIR%\src
copy ..\lambda_handler.py %PACKAGE_DIR%\

REM Remove unnecessary files to reduce package size
echo Removing unnecessary files...
cd %PACKAGE_DIR%
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
for /d /r . %%d in (tests) do @if exist "%%d" rmdir /s /q "%%d"
for /d /r . %%d in (*.dist-info) do @if exist "%%d" rmdir /s /q "%%d"
for /d /r . %%d in (*.egg-info) do @if exist "%%d" rmdir /s /q "%%d"
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul

REM Create ZIP file (requires PowerShell or 7-Zip)
echo Creating deployment package...
cd ..
powershell Compress-Archive -Path %PACKAGE_DIR%\* -DestinationPath %ZIP_FILE% -Force

echo =========================================
echo Deployment package created successfully!
echo File: %ZIP_FILE%
echo =========================================

echo.
echo Next steps:
echo 1. Upload %ZIP_FILE% to AWS Lambda
echo 2. Set environment variables in Lambda configuration
echo 3. Configure EventBridge schedule
echo.

pause
