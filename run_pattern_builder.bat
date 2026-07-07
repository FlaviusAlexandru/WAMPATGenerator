@echo off
setlocal

if exist "%~dp0.venv\Scripts\pythonw.exe" (
	"%~dp0.venv\Scripts\pythonw.exe" "%~dp0unity_pattern_builder.py"
	exit /b %errorlevel%
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
	pythonw "%~dp0unity_pattern_builder.py"
	exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
	python "%~dp0unity_pattern_builder.py"
	exit /b %errorlevel%
)

echo Python was not found.
exit /b 1