@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:menu
cls
echo.
echo ========================================
echo       하나 AI 학원 - 하나봇 메뉴
echo ========================================
echo.
echo 1. 하나봇에게 질문 (RAG 없음)
echo 2. 하나봇에게 질문 (RAG)
echo 3. RAG 있음/없음 비교
echo 4. 파인튜닝 비교 (4가지)
echo.
echo 0. 종료
echo ========================================
echo.
set /p choice="선택 (0-4): "

if "%choice%"=="1" (
    cls
    python chat_no_rag.py
    pause
    goto menu
)

if "%choice%"=="2" (
    cls
    python chat_with_rag.py
    pause
    goto menu
)

if "%choice%"=="3" (
    cls
    python compare.py
    goto menu
)

if "%choice%"=="4" (
    cls
    python ..\labs\1-3\compare_ft.py
    pause
    goto menu
)

if "%choice%"=="0" (
    exit /b 0
)

goto menu
