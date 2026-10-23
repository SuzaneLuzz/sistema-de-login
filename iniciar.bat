@echo off
chcp 65001 >nul
title Sistema de Login
cd /d "%~dp0"

echo ==================================================
echo   Sistema de Login - preparando tudo...
echo ==================================================
echo.

rem 1. Procura o Python
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [ERRO] Python nao encontrado.
    echo Instale pelo site python.org e marque a opcao "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

rem 2. Cria o ambiente virtual na primeira vez
if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual ^(so na primeira vez^)...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Nao foi possivel criar o ambiente virtual.
        pause
        exit /b 1
    )
)

rem 3. Instala as dependencias
echo Verificando dependencias...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar as dependencias. Verifique sua internet.
    pause
    exit /b 1
)

rem 4. Cria o .env a partir do modelo
if not exist ".env" copy ".env.example" ".env" >nul

rem 5. Inicia o servidor (o navegador abre sozinho)
".venv\Scripts\python.exe" app.py
echo.
pause
