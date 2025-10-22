# Примеры использования

## Базовое использование

### Запуск с настройками по умолчанию

```bash
# Windows
run.bat

# Linux/Mac
chmod +x run.sh
./run.sh

# Или напрямую
python tg_socks5_proxy.py
```

## Настройка конфигурации

### Пример 1: Только быстрые прокси

Измените в `config.py`:

```python
MAX_PING = 100  # Только прокси с пингом < 100ms
```

### Пример 2: Использовать прокси только из определенных стран

```python
# Только европейские прокси
ALLOWED_COUNTRIES = ["DE", "FR", "NL", "AT", "SE"]
```

### Пример 3: Исключить определенные страны

```python
# Исключить прокси из определенных стран
EXCLUDED_COUNTRIES = ["CN", "RU"]
```

### Пример 4: Изменить локальный порт

```python
# Если порт 1080 занят, используйте другой
LOCAL_PORT = 1085
```

### Пример 5: Разрешить подключения из локальной сети

⚠️ **ВНИМАНИЕ**: Это может быть небезопасно в публичных сетях!

```python
# Разрешить подключения с любого IP в локальной сети
LOCAL_HOST = "0.0.0.0"
```

### Пример 6: Настройка таймаутов

```python
# Увеличить таймауты для медленных соединений
CONNECTION_TIMEOUT = 20
CLIENT_TIMEOUT = 20
SOCKS_TIMEOUT = 10
```

### Пример 7: Частое обновление списка прокси

```python
# Обновлять список каждые 5 минут
UPDATE_INTERVAL = 300
```

## Использование с Telegram

### Telegram Desktop

1. **Открыть настройки прокси:**
   - `Settings` → `Advanced` → `Connection type`
   - Или используйте горячие клавиши: `Ctrl+Alt+Shift+P` (Windows/Linux) или `Cmd+Option+Shift+P` (Mac)

2. **Добавить SOCKS5 прокси:**
   ```
   Server: 127.0.0.1
   Port: 1080
   Username: (пусто)
   Password: (пусто)
   ```

3. **Активировать прокси:**
   - Установите галочку "Use custom proxy"
   - Нажмите "Save"

### Telegram Android

1. Откройте `Settings` → `Data and Storage` → `Proxy Settings`
2. Нажмите `Add Proxy` → `SOCKS5`
3. Введите данные:
   ```
   Server: 127.0.0.1
   Port: 1080
   Username: (пусто)
   Password: (пусто)
   ```
4. Включите прокси

### Telegram iOS

1. Откройте `Settings` → `Data and Storage` → `Use Proxy`
2. Нажмите `Add Proxy` → `SOCKS5`
3. Введите данные:
   ```
   Server: 127.0.0.1
   Port: 1080
   Username: (пусто)
   Password: (пусто)
   ```
4. Активируйте прокси

## Расширенные сценарии

### Запуск в фоновом режиме (Linux/Mac)

```bash
# Запуск в фоне
nohup python3 tg_socks5_proxy.py > proxy.log 2>&1 &

# Проверить, что прокси работает
ps aux | grep tg_socks5_proxy

# Остановить прокси
pkill -f tg_socks5_proxy.py
```

### Запуск как системный сервис (Linux systemd)

Создайте файл `/etc/systemd/system/tg-proxy.service`:

```ini
[Unit]
Description=Telegram SOCKS5 Proxy
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/proxy
ExecStart=/usr/bin/python3 /path/to/proxy/tg_socks5_proxy.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tg-proxy
sudo systemctl start tg-proxy
sudo systemctl status tg-proxy
```

### Автозапуск при входе в систему (Windows)

1. Создайте ярлык для `run.bat`
2. Нажмите `Win+R` и введите `shell:startup`
3. Скопируйте ярлык в открывшуюся папку

### Мониторинг логов

```bash
# Linux/Mac
tail -f proxy.log

# Windows PowerShell
Get-Content proxy.log -Wait -Tail 50
```

## Проверка работоспособности

### Проверка локального прокси

```bash
# Linux/Mac
curl --socks5 127.0.0.1:1080 https://api.telegram.org/bot

# Windows PowerShell
Invoke-WebRequest -Uri "https://api.telegram.org/bot" -Proxy "socks5://127.0.0.1:1080"
```

### Проверка подключения к Telegram

1. Запустите прокси
2. Настройте Telegram для использования прокси
3. В логах прокси вы должны увидеть подключения:
   ```
   [2025-10-22 12:00:00] Выбран прокси: 185.175.58.113:1080 ...
   [2025-10-22 12:00:00] SOCKS5 прокси запущен на 127.0.0.1:1080
   ```

## Оптимизация производительности

### Использование только самых быстрых прокси

```python
MAX_PING = 50  # Очень строгий фильтр
ALLOWED_COUNTRIES = ["DE", "NL", "FR"]  # Европейские прокси обычно быстрее
```

### Увеличение размера буфера

```python
BUFFER_SIZE = 16384  # Больше буфер = быстрее передача данных
```

## Устранение проблем

### Прокси не запускается

```
Ошибка: Address already in use
```

**Решение**: Порт 1080 занят. Измените `LOCAL_PORT` в `config.py`:

```python
LOCAL_PORT = 1085
```

### Нет доступных прокси

```
ERROR: Не найдено подходящих прокси
```

**Решение**: Ослабьте фильтры в `config.py`:

```python
MAX_PING = 500  # Увеличить максимальный пинг
ALLOWED_COUNTRIES = []  # Убрать фильтр по странам
```

### Telegram не подключается

**Проверьте:**
1. Прокси запущен и работает
2. В настройках Telegram указан правильный адрес (`127.0.0.1`) и порт (`1080`)
3. В логах прокси нет ошибок
4. Firewall не блокирует подключения

## Коды стран (ISO 3166-1 alpha-2)

Часто используемые коды:
- `US` - США
- `DE` - Германия
- `FR` - Франция
- `NL` - Нидерланды
- `GB` - Великобритания
- `SE` - Швеция
- `AT` - Австрия
- `SG` - Сингапур
- `JP` - Япония
- `AU` - Австралия

Полный список: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2

