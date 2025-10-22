@echo off
REM Запуск Telegram SOCKS5 Proxy для Windows
echo ========================================
echo Telegram SOCKS5 Proxy
echo ========================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден!
    echo Установите Python 3.7+ с https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Запуск прокси
echo Запуск прокси...
echo.
python tg_socks5_proxy.py

pause

