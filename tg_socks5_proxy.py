#!/usr/bin/env python3
"""
Telegram SOCKS5 Proxy
Автоматически подключается к прокси с пингом < 300 из списка
"""

import asyncio
import socket
import json
import random
import time
import sys
from urllib.request import urlopen
from urllib.error import URLError

# Импортируем конфигурацию
try:
    from config import (
        PROXY_LIST_URL, MAX_PING, LOCAL_HOST, LOCAL_PORT,
        UPDATE_INTERVAL, BUFFER_SIZE, CONNECTION_TIMEOUT,
        CLIENT_TIMEOUT, SOCKS_TIMEOUT, VERBOSE,
        ALLOWED_COUNTRIES, EXCLUDED_COUNTRIES, MIN_PROXY_AGE
    )
except ImportError:
    # Значения по умолчанию, если config.py отсутствует
    PROXY_LIST_URL = "https://raw.githubusercontent.com/hookzof/socks5_list/refs/heads/master/tg/socks.json"
    MAX_PING = 300
    LOCAL_HOST = "127.0.0.1"
    LOCAL_PORT = 1080
    UPDATE_INTERVAL = 600
    BUFFER_SIZE = 8192
    CONNECTION_TIMEOUT = 10
    CLIENT_TIMEOUT = 10
    SOCKS_TIMEOUT = 5
    VERBOSE = False  # По умолчанию минимальное логирование
    ALLOWED_COUNTRIES = []
    EXCLUDED_COUNTRIES = []
    MIN_PROXY_AGE = 0

# Глобальные переменные
current_proxy = None
proxy_list = []
proxy_blacklist = set()  # Черный список неработающих прокси
connection_errors = 0  # Счетчик ошибок подключения
last_proxy_switch = 0  # Время последней смены прокси
invalid_socks_count = 0  # Счетчик неверных SOCKS подключений
successful_connections = 0  # Счетчик успешных подключений
total_connections = 0  # Общее количество попыток подключений


def print_info(msg):
    """Вывод информационных сообщений"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def print_error(msg):
    """Вывод ошибок"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ERROR: {msg}", file=sys.stderr, flush=True)


def load_proxy_list():
    """Загружает список прокси из JSON"""
    global proxy_list
    
    try:
        print_info(f"Загрузка списка прокси из {PROXY_LIST_URL}...")
        with urlopen(PROXY_LIST_URL, timeout=10) as response:
            data = response.read().decode('utf-8')
            proxies = json.loads(data)
            
        total_count = len(proxies)
        
        # Фильтруем прокси с пингом меньше MAX_PING
        filtered = [p for p in proxies if p.get('ping', 9999) < MAX_PING]
        
        # Фильтруем по странам (если указано)
        if ALLOWED_COUNTRIES:
            filtered = [p for p in filtered if p.get('country', '') in ALLOWED_COUNTRIES]
            
        # Исключаем определенные страны
        if EXCLUDED_COUNTRIES:
            filtered = [p for p in filtered if p.get('country', '') not in EXCLUDED_COUNTRIES]
        
        # Фильтруем по возрасту прокси
        if MIN_PROXY_AGE > 0:
            current_time = int(time.time())
            filtered = [p for p in filtered 
                       if current_time - p.get('addTime', current_time) >= MIN_PROXY_AGE]
        
        if filtered:
            proxy_list = filtered
            msg = f"Загружено {len(filtered)} прокси (из {total_count} всего)"
            if ALLOWED_COUNTRIES:
                msg += f" для стран: {', '.join(ALLOWED_COUNTRIES)}"
            print_info(msg)
            return True
        else:
            print_error(f"Не найдено подходящих прокси")
            return False
            
    except (URLError, json.JSONDecodeError) as e:
        print_error(f"Ошибка загрузки списка прокси: {e}")
        return False


def select_random_proxy():
    """Выбирает случайный прокси из списка, исключая blacklist"""
    global current_proxy, last_proxy_switch, connection_errors
    
    if not proxy_list:
        return None
    
    # Фильтруем прокси, исключая те, что в blacklist
    available_proxies = [
        p for p in proxy_list 
        if f"{p['ip']}:{p['port']}" not in proxy_blacklist
    ]
    
    if not available_proxies:
        print_error("Все прокси в blacklist! Очищаем blacklist...")
        proxy_blacklist.clear()
        available_proxies = proxy_list
    
    proxy = random.choice(available_proxies)
    current_proxy = proxy
    last_proxy_switch = time.time()
    connection_errors = 0
    
    print_info(f"Выбран прокси: {proxy['ip']}:{proxy['port']} "
               f"(страна: {proxy.get('country', 'N/A')}, пинг: {proxy.get('ping', 'N/A')}ms, "
               f"провайдер: {proxy.get('provider', 'N/A')})")
    
    if proxy_blacklist:
        print_info(f"В blacklist: {len(proxy_blacklist)} прокси")
    
    return proxy


def add_to_blacklist(proxy_ip, proxy_port, reason="неизвестно"):
    """Добавляет прокси в черный список"""
    global proxy_blacklist
    proxy_key = f"{proxy_ip}:{proxy_port}"
    if proxy_key not in proxy_blacklist:
        proxy_blacklist.add(proxy_key)
        print_error(f"Прокси {proxy_key} добавлен в blacklist ({reason})")


def should_switch_proxy():
    """Проверяет, нужно ли переключиться на другой прокси"""
    global connection_errors, last_proxy_switch
    
    MAX_ERRORS = 3  # Максимум ошибок до смены прокси
    MIN_SWITCH_INTERVAL = 30  # Минимальный интервал между сменами (секунды)
    
    if connection_errors >= MAX_ERRORS:
        time_since_switch = time.time() - last_proxy_switch
        if time_since_switch >= MIN_SWITCH_INTERVAL:
            return True
    return False


async def connect_to_upstream(proxy_ip, proxy_port, dest_host, dest_port):
    """Подключается к upstream SOCKS5 прокси"""
    try:
        # Подключаемся к upstream SOCKS5 прокси
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(proxy_ip, proxy_port),
            timeout=CONNECTION_TIMEOUT
        )
        
        # SOCKS5 приветствие
        writer.write(b'\x05\x01\x00')  # VER=5, NMETHODS=1, METHOD=0 (no auth)
        await writer.drain()
        
        # Читаем ответ
        response = await asyncio.wait_for(reader.readexactly(2), timeout=SOCKS_TIMEOUT)
        if response != b'\x05\x00':
            raise Exception(f"SOCKS5 handshake failed: {response.hex()}")
        
        # Отправляем запрос на подключение
        # VER=5, CMD=1 (CONNECT), RSV=0, ATYP=3 (domain name)
        request = b'\x05\x01\x00\x03'
        request += bytes([len(dest_host)]) + dest_host.encode()
        request += dest_port.to_bytes(2, 'big')
        
        writer.write(request)
        await writer.drain()
        
        # Читаем ответ
        response = await asyncio.wait_for(reader.readexactly(4), timeout=SOCKS_TIMEOUT)
        if response[1] != 0x00:
            raise Exception(f"SOCKS5 connect failed, status: {response[1]}")
        
        # Читаем остаток ответа (адрес и порт)
        atyp = response[3]
        if atyp == 0x01:  # IPv4
            await reader.readexactly(6)
        elif atyp == 0x03:  # Domain
            addr_len = (await reader.readexactly(1))[0]
            await reader.readexactly(addr_len + 2)
        elif atyp == 0x04:  # IPv6
            await reader.readexactly(18)
        
        return reader, writer
        
    except Exception as e:
        raise Exception(f"Не удалось подключиться к upstream прокси: {e}")


async def handle_socks5_client(client_reader, client_writer):
    """Обрабатывает SOCKS5 клиента"""
    global connection_errors, invalid_socks_count, successful_connections, total_connections
    upstream_writer = None
    
    try:
        client_addr = client_writer.get_extra_info('peername')
        
        # Читаем приветствие от клиента
        greeting = await asyncio.wait_for(client_reader.readexactly(2), timeout=CLIENT_TIMEOUT)
        if greeting[0] != 0x05:
            invalid_socks_count += 1
            # Логируем только каждое 10-е неверное подключение
            if invalid_socks_count % 10 == 1 or VERBOSE:
                print_error(f"Неверная версия SOCKS: {greeting[0]} (всего: {invalid_socks_count})")
            return
        
        # Читаем методы аутентификации
        nmethods = greeting[1]
        methods = await client_reader.readexactly(nmethods)
        
        # Отправляем ответ (no authentication required)
        client_writer.write(b'\x05\x00')
        await client_writer.drain()
        
        # Читаем запрос на подключение
        request = await asyncio.wait_for(client_reader.readexactly(4), timeout=CLIENT_TIMEOUT)
        
        if request[0] != 0x05 or request[1] != 0x01:  # VER != 5 or CMD != CONNECT
            client_writer.write(b'\x05\x07\x00\x01' + b'\x00' * 6)  # Command not supported
            await client_writer.drain()
            return
        
        # Читаем адрес назначения
        atyp = request[3]
        if atyp == 0x01:  # IPv4
            addr_bytes = await client_reader.readexactly(4)
            dest_addr = socket.inet_ntoa(addr_bytes)
        elif atyp == 0x03:  # Domain name
            addr_len = (await client_reader.readexactly(1))[0]
            dest_addr = (await client_reader.readexactly(addr_len)).decode()
        elif atyp == 0x04:  # IPv6
            addr_bytes = await client_reader.readexactly(16)
            dest_addr = socket.inet_ntop(socket.AF_INET6, addr_bytes)
        else:
            client_writer.write(b'\x05\x08\x00\x01' + b'\x00' * 6)  # Address type not supported
            await client_writer.drain()
            return
        
        dest_port = int.from_bytes(await client_reader.readexactly(2), 'big')
        
        # Подключаемся к upstream прокси
        if not current_proxy:
            raise Exception("Прокси не выбран")
        
        total_connections += 1
        
        upstream_reader, upstream_writer = await connect_to_upstream(
            current_proxy['ip'],
            current_proxy['port'],
            dest_addr,
            dest_port
        )
        
        # Успешное подключение!
        successful_connections += 1
        print_info(f"✓ Подключено к {dest_addr}:{dest_port} через прокси "
                   f"{current_proxy['ip']}:{current_proxy['port']} "
                   f"({current_proxy.get('country', 'N/A')}) "
                   f"[Успешных: {successful_connections}/{total_connections}]")
        
        # Отправляем успешный ответ клиенту
        client_writer.write(b'\x05\x00\x00\x01' + b'\x00' * 6)
        await client_writer.drain()
        
        # Проксируем данные
        async def forward(reader, writer, direction):
            try:
                while True:
                    data = await reader.read(BUFFER_SIZE)
                    if not data:
                        break
                    writer.write(data)
                    await writer.drain()
            except:
                pass
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except:
                    pass
        
        # Запускаем двустороннюю передачу данных
        await asyncio.gather(
            forward(client_reader, upstream_writer, "client->upstream"),
            forward(upstream_reader, client_writer, "upstream->client"),
            return_exceptions=True
        )
        
    except Exception as e:
        error_msg = str(e)
        
        # Если ошибка связана с upstream прокси
        if "upstream" in error_msg.lower() or "connect" in error_msg.lower():
            connection_errors += 1
            
            # Добавляем прокси в blacklist если он явно не работает
            if current_proxy:
                if connection_errors % 3 == 0:  # Логируем каждую 3-ю ошибку
                    print_error(f"Ошибка подключения к upstream ({connection_errors}): {e}")
                
                if connection_errors >= 3:
                    add_to_blacklist(current_proxy['ip'], current_proxy['port'], 
                                   "множественные ошибки подключения")
            
            # Проверяем, нужно ли переключиться на другой прокси
            if should_switch_proxy():
                print_info("Слишком много ошибок, переключаемся на другой прокси...")
                select_random_proxy()
        else:
            # Другие ошибки логируем только в verbose режиме
            if VERBOSE:
                print_error(f"Ошибка обработки клиента: {e}")
    finally:
        try:
            client_writer.close()
            await client_writer.wait_closed()
        except:
            pass
        if upstream_writer:
            try:
                upstream_writer.close()
                await upstream_writer.wait_closed()
            except:
                pass


async def update_proxy_list_periodically():
    """Периодически обновляет список прокси"""
    while True:
        await asyncio.sleep(UPDATE_INTERVAL)
        print_info("Обновление списка прокси...")
        load_proxy_list()
        if proxy_list:
            select_random_proxy()


async def print_statistics_periodically():
    """Периодически выводит статистику работы"""
    STATS_INTERVAL = 300  # Каждые 5 минут
    
    while True:
        await asyncio.sleep(STATS_INTERVAL)
        
        if total_connections > 0:
            success_rate = (successful_connections / total_connections * 100)
            print_info("=" * 60)
            print_info(f"📊 Статистика за последние {STATS_INTERVAL // 60} минут:")
            print_info(f"  ✓ Успешных подключений: {successful_connections}/{total_connections} ({success_rate:.1f}%)")
            print_info(f"  ✗ Неверных SOCKS запросов: {invalid_socks_count}")
            print_info(f"  🚫 Прокси в blacklist: {len(proxy_blacklist)}")
            if current_proxy:
                print_info(f"  🌍 Текущий прокси: {current_proxy['ip']}:{current_proxy['port']} ({current_proxy.get('country', 'N/A')})")
            print_info("=" * 60)


async def clean_blacklist_periodically():
    """Периодически очищает старые записи из blacklist"""
    CLEAN_INTERVAL = 1800  # Каждые 30 минут
    
    while True:
        await asyncio.sleep(CLEAN_INTERVAL)
        
        if proxy_blacklist:
            old_count = len(proxy_blacklist)
            # Очищаем половину blacklist, давая прокси второй шанс
            remove_count = old_count // 2
            if remove_count > 0:
                to_remove = list(proxy_blacklist)[:remove_count]
                for proxy_key in to_remove:
                    proxy_blacklist.remove(proxy_key)
                print_info(f"🔄 Очищено {remove_count} прокси из blacklist ({old_count} -> {len(proxy_blacklist)})")


async def handle_http_request(reader, writer):
    """Обрабатывает HTTP запрос для веб-интерфейса"""
    try:
        addr = writer.get_extra_info('peername')
        
        # Читаем HTTP запрос
        request_line = await reader.readline()
        request_line = request_line.decode('utf-8').strip()
        
        if not request_line:
            return
        
        # Парсим путь
        parts = request_line.split()
        if len(parts) < 2:
            return
        
        path = parts[1]
        
        # Читаем заголовки
        while True:
            line = await reader.readline()
            if line == b'\r\n' or line == b'\n' or not line:
                break
        
        # Генерируем ответ
        if path == '/' or path == '/index.html':
            response = generate_web_interface()
        elif path == '/api/status':
            response = generate_status_json()
        else:
            response = generate_404()
        
        writer.write(response.encode('utf-8'))
        await writer.drain()
        
    except Exception as e:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except:
            pass


def generate_web_interface():
    """Генерирует веб-интерфейс"""
    import json
    
    success_rate = 0
    if total_connections > 0:
        success_rate = (successful_connections / total_connections * 100)
    
    proxy_info = "Не выбран"
    if current_proxy:
        proxy_info = f"{current_proxy['ip']}:{current_proxy['port']} ({current_proxy.get('country', 'N/A')})"
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram SOCKS5 Proxy - Панель управления</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
        }}
        h1 {{
            font-size: 2.5em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        .subtitle {{ color: #666; font-size: 1.1em; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .stat-title {{
            font-size: 0.9em;
            color: #999;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .proxy-info {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .proxy-info h2 {{
            color: #667eea;
            margin-bottom: 15px;
        }}
        .info-item {{
            padding: 10px;
            margin: 5px 0;
            background: #f5f5f5;
            border-radius: 8px;
        }}
        .info-label {{
            font-weight: bold;
            color: #667eea;
        }}
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #4caf50;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .footer {{
            text-align: center;
            color: white;
            margin-top: 20px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Telegram SOCKS5 Proxy</h1>
            <p class="subtitle">Панель управления и мониторинга</p>
            <div style="margin-top: 15px;">
                <span class="status-indicator"></span>
                <span style="color: #4caf50; font-weight: bold;">Работает</span>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-title">✅ Успешных подключений</div>
                <div class="stat-value">{successful_connections}</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">📊 Всего попыток</div>
                <div class="stat-value">{total_connections}</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">📈 Процент успеха</div>
                <div class="stat-value">{success_rate:.1f}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">🚫 В blacklist</div>
                <div class="stat-value">{len(proxy_blacklist)}</div>
            </div>
        </div>
        
        <div class="proxy-info">
            <h2>📡 Информация о прокси</h2>
            <div class="info-item">
                <span class="info-label">Текущий прокси:</span> {proxy_info}
            </div>
            <div class="info-item">
                <span class="info-label">Локальный адрес:</span> {LOCAL_HOST}:{LOCAL_PORT}
            </div>
            <div class="info-item">
                <span class="info-label">Доступных прокси:</span> {len(proxy_list)}
            </div>
            <div class="info-item">
                <span class="info-label">Неверных SOCKS:</span> {invalid_socks_count}
            </div>
        </div>
        
        <div class="footer">
            Powered by Python asyncio ⚡ | Обновляется автоматически
        </div>
    </div>
    
    <script>
        setTimeout(() => location.reload(), 5000);
    </script>
</body>
</html>"""
    
    response = "HTTP/1.1 200 OK\r\n"
    response += "Content-Type: text/html; charset=utf-8\r\n"
    response += f"Content-Length: {len(html.encode('utf-8'))}\r\n"
    response += "Connection: close\r\n\r\n"
    response += html
    
    return response


def generate_status_json():
    """Генерирует JSON со статусом"""
    import json
    
    success_rate = 0
    if total_connections > 0:
        success_rate = (successful_connections / total_connections * 100)
    
    data = {
        "status": "ok",
        "proxy": {
            "current": f"{current_proxy['ip']}:{current_proxy['port']}" if current_proxy else None,
            "country": current_proxy.get('country') if current_proxy else None,
            "available": len(proxy_list),
            "blacklisted": len(proxy_blacklist)
        },
        "connections": {
            "successful": successful_connections,
            "total": total_connections,
            "success_rate": round(success_rate, 2)
        },
        "errors": {
            "invalid_socks": invalid_socks_count,
            "connection_errors": connection_errors
        },
        "timestamp": int(time.time())
    }
    
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    
    response = "HTTP/1.1 200 OK\r\n"
    response += "Content-Type: application/json; charset=utf-8\r\n"
    response += f"Content-Length: {len(json_str.encode('utf-8'))}\r\n"
    response += "Connection: close\r\n\r\n"
    response += json_str
    
    return response


def generate_404():
    """Генерирует 404 страницу"""
    html = "<h1>404 Not Found</h1>"
    response = "HTTP/1.1 404 Not Found\r\n"
    response += "Content-Type: text/html\r\n"
    response += f"Content-Length: {len(html)}\r\n"
    response += "Connection: close\r\n\r\n"
    response += html
    return response


async def main():
    """Главная функция"""
    print_info("=" * 60)
    print_info("Telegram SOCKS5 Proxy")
    print_info("=" * 60)
    
    # Загружаем начальный список прокси
    if not load_proxy_list():
        print_error("Не удалось загрузить список прокси. Выход.")
        return
    
    # Выбираем случайный прокси
    if not select_random_proxy():
        print_error("Не удалось выбрать прокси. Выход.")
        return
    
    # Запускаем фоновые задачи
    asyncio.create_task(update_proxy_list_periodically())
    asyncio.create_task(print_statistics_periodically())
    asyncio.create_task(clean_blacklist_periodically())
    
    # Запускаем SOCKS5 сервер
    socks_server = await asyncio.start_server(
        handle_socks5_client,
        LOCAL_HOST,
        LOCAL_PORT
    )
    
    # Запускаем HTTP сервер (веб-интерфейс)
    http_server = await asyncio.start_server(
        handle_http_request,
        "0.0.0.0",
        5000
    )
    
    socks_addr = socks_server.sockets[0].getsockname()
    http_addr = http_server.sockets[0].getsockname()
    
    print_info("=" * 60)
    print_info(f"✅ SOCKS5 прокси запущен на {socks_addr[0]}:{socks_addr[1]}")
    print_info(f"✅ Веб-интерфейс запущен на http://{http_addr[0]}:{http_addr[1]}")
    print_info(f"🌍 Upstream прокси: {current_proxy['ip']}:{current_proxy['port']}")
    print_info("=" * 60)
    print_info(f"Настройте Telegram для использования SOCKS5 прокси:")
    print_info(f"  Сервер: {socks_addr[0]}")
    print_info(f"  Порт: {socks_addr[1]}")
    print_info("=" * 60)
    print_info(f"🌐 Откройте в браузере: http://localhost:{http_addr[1]}")
    print_info("=" * 60)
    
    async with socks_server, http_server:
        await asyncio.gather(
            socks_server.serve_forever(),
            http_server.serve_forever()
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_info("\nОстановка прокси...")
    except Exception as e:
        print_error(f"Критическая ошибка: {e}")
        sys.exit(1)

