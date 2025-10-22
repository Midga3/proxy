#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работоспособности прокси
"""

import socket
import sys
import time

def test_proxy(host='127.0.0.1', port=1080):
    """Тестирует подключение к SOCKS5 прокси"""
    print(f"Проверка SOCKS5 прокси на {host}:{port}...")
    print("-" * 60)
    
    try:
        # Создаем сокет
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        # Подключаемся к прокси
        print(f"[1/4] Подключение к {host}:{port}...", end=" ")
        sock.connect((host, port))
        print("✓ OK")
        
        # SOCKS5 приветствие
        print("[2/4] Отправка SOCKS5 приветствия...", end=" ")
        sock.send(b'\x05\x01\x00')
        response = sock.recv(2)
        if response != b'\x05\x00':
            print(f"✗ ОШИБКА: неверный ответ {response.hex()}")
            return False
        print("✓ OK")
        
        # Запрос подключения к тестовому серверу
        print("[3/4] Тестовое подключение через прокси...", end=" ")
        # Подключаемся к api.telegram.org:443
        request = b'\x05\x01\x00\x03'  # VER, CMD=CONNECT, RSV, ATYP=DOMAIN
        request += b'\x0f' + b'api.telegram.org'  # длина + домен
        request += (443).to_bytes(2, 'big')  # порт
        
        sock.send(request)
        response = sock.recv(4)
        
        if len(response) < 4:
            print("✗ ОШИБКА: слишком короткий ответ")
            return False
            
        if response[1] != 0x00:
            error_codes = {
                0x01: "общая ошибка SOCKS сервера",
                0x02: "подключение не разрешено правилами",
                0x03: "сеть недоступна",
                0x04: "хост недоступен",
                0x05: "отказано в соединении",
                0x06: "TTL истек",
                0x07: "команда не поддерживается",
                0x08: "тип адреса не поддерживается"
            }
            error = error_codes.get(response[1], f"неизвестная ошибка {response[1]}")
            print(f"✗ ОШИБКА: {error}")
            return False
        
        # Читаем остаток ответа
        atyp = response[3]
        if atyp == 0x01:  # IPv4
            sock.recv(6)
        elif atyp == 0x03:  # Domain
            addr_len = ord(sock.recv(1))
            sock.recv(addr_len + 2)
        elif atyp == 0x04:  # IPv6
            sock.recv(18)
        
        print("✓ OK")
        
        # Проверка связи
        print("[4/4] Проверка передачи данных...", end=" ")
        # Отправляем простой HTTP запрос
        sock.send(b'GET / HTTP/1.0\r\nHost: api.telegram.org\r\n\r\n')
        data = sock.recv(100)
        if data and b'HTTP' in data:
            print("✓ OK")
        else:
            print("✗ ПРЕДУПРЕЖДЕНИЕ: нет ответа")
        
        sock.close()
        
        print("-" * 60)
        print("✓ Прокси работает корректно!")
        print()
        print("Вы можете использовать его в Telegram:")
        print(f"  Сервер: {host}")
        print(f"  Порт: {port}")
        print(f"  Тип: SOCKS5")
        return True
        
    except socket.timeout:
        print("✗ ОШИБКА: превышен таймаут")
        print("\nВозможные причины:")
        print("  - Прокси не запущен")
        print("  - Указан неверный адрес или порт")
        print("  - Firewall блокирует подключение")
        return False
        
    except ConnectionRefusedError:
        print("✗ ОШИБКА: отказано в подключении")
        print("\nВозможные причины:")
        print("  - Прокси не запущен")
        print("  - Указан неверный порт")
        print("  - Прокси слушает на другом адресе")
        print("\nЗапустите прокси командой:")
        print("  python tg_socks5_proxy.py")
        return False
        
    except Exception as e:
        print(f"✗ ОШИБКА: {e}")
        return False
    
    finally:
        try:
            sock.close()
        except:
            pass


def main():
    """Главная функция"""
    print("=" * 60)
    print("Тест SOCKS5 прокси для Telegram")
    print("=" * 60)
    print()
    
    # Проверяем аргументы
    host = '127.0.0.1'
    port = 1080
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print("ОШИБКА: порт должен быть числом")
            sys.exit(1)
    
    success = test_proxy(host, port)
    
    if success:
        sys.exit(0)
    else:
        print()
        print("Устранение неполадок:")
        print("  1. Убедитесь, что прокси запущен")
        print("  2. Проверьте адрес и порт")
        print("  3. Проверьте настройки firewall")
        print("  4. Посмотрите логи прокси на наличие ошибок")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nТест прерван пользователем")
        sys.exit(1)

