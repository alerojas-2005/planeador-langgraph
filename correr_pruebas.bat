@echo off
REM correr_pruebas.bat - Pruebas del Taller 1 (doble clic para ejecutar).
REM 1) crea .venv e instala dependencias  2) descarga qwen2.5:3b
REM 3) pruebas de herramientas sin modelo  4) seis preguntas + reto de memoria
REM La evidencia queda en docs\evidencias\
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
where python >nul 2>nul || (echo No se encontro Python. & pause & exit /b 1)
where ollama >nul 2>nul || (echo No se encontro Ollama. Instalalo desde https://ollama.com/download & pause & exit /b 1)
if not exist .venv\Scripts\python.exe python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -q -r backend\requirements.txt pytest || (pause & exit /b 1)
ollama pull qwen2.5:3b || (pause & exit /b 1)
if not exist docs\evidencias mkdir docs\evidencias
python -m pytest tests\test_herramientas.py -v -p no:cacheprovider > docs\evidencias\salida_pytest_windows.txt 2>&1
type docs\evidencias\salida_pytest_windows.txt
python -m tests.ejecutar_pruebas --reto --salida docs\evidencias
echo Listo. Evidencia en docs\evidencias\
pause
