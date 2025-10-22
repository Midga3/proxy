#!/bin/bash
# Запуск Telegram SOCKS5 Proxy для Linux/Mac

echo "========================================"
echo "Telegram SOCKS5 Proxy"
echo "========================================"
echo ""

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "ОШИБКА: Python 3 не найден!"
    echo "Установите Python 3.7+ с помощью вашего менеджера пакетов"
    exit 1
fi

# Проверка версии Python
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Найден Python $PYTHON_VERSION"

# Запуск прокси
echo "Запуск прокси..."
echo ""
python3 tg_socks5_proxy.py

