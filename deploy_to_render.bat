@echo off
setlocal EnableDelayedExpansion
title 1-Click Upload and Deploy to Render - Cyber Hermes Agent
color 0A

echo ===============================================================================
echo   CYBER HERMES AGENT - 1-CLICK UPLOAD AND DEPLOY TO RENDER
echo ===============================================================================
echo.

cd /d "%~dp0"

echo [*] Checking git repository status...
git rev-parse --is-inside-work-tree >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo [ERROR] Not inside a git repository!
    pause
    exit /b 1
)

echo [*] Staging all modified and new files...
git add -A

git diff --cached --quiet
if %ERRORLEVEL% EQU 0 (
    echo [i] No new changes detected to commit.
    echo [*] Checking remote branch synchronization...
) else (
    set "COMMIT_MSG=%~1"
    if "!COMMIT_MSG!"=="" (
        for /f %%a in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"') do set "STAMP=%%a"
        set "COMMIT_MSG=Auto-deploy update: !STAMP!"
    )
    echo [*] Committing changes: "!COMMIT_MSG!"
    git commit -m "!COMMIT_MSG!"
)

echo.
echo [*] Pushing latest code to GitHub (main branch)...
set "GITHUB_PAT="
if exist "%~dp0.deploy_token" (
    set /p GITHUB_PAT=<"%~dp0.deploy_token"
)
if "!GITHUB_PAT!"=="" (
    if defined GITHUB_TOKEN (
        set "GITHUB_PAT=%GITHUB_TOKEN%"
    )
)
if "!GITHUB_PAT!"=="" (
    color 0C
    echo.
    echo [ERROR] No GitHub token found in .deploy_token or GITHUB_TOKEN environment variable!
    pause
    exit /b 1
)

git -c credential.helper= push "https://cyberdrivepro:!GITHUB_PAT!@github.com/cyberdrivepro/hermes-telegram-agent.git" main

if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo.
    echo [ERROR] Push to GitHub failed! Please check your internet connection or git status.
    pause
    exit /b 1
)

echo.
echo ===============================================================================
echo   SUCCESS! ALL FILES UPLOADED TO GITHUB AND RENDER DEPLOY TRIGGERED!
echo ===============================================================================
echo.
echo   * GitHub Repo: https://github.com/cyberdrivepro/hermes-telegram-agent
echo   * Render Deploy: Render is now building and deploying the latest code.
echo   * Telegram Bot: @CyberMastetControlAi_bot
echo.
echo   Cloud build typically finishes in 60-90 seconds.
echo ===============================================================================
echo.
pause
