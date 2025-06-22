@echo off
echo Установка зависимостей для Telegram бота...
echo.

REM Проверка наличия Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Ошибка: Python не установлен или не найден в PATH.
    echo Пожалуйста, установите Python (версия 3.8 или выше) и запустите скрипт снова.
    pause
    exit /b 1
)

REM Создание виртуального окружения
echo Создание виртуального окружения...
python -m venv .venv
if %ERRORLEVEL% neq 0 (
    echo Ошибка при создании виртуального окружения.
    pause
    exit /b 1
)

REM Активация виртуального окружения
echo Активация виртуального окружения...
call .venv\Scripts\activate.bat

REM Установка зависимостей
echo Установка зависимостей...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo Ошибка при установке зависимостей.
    pause
    exit /b 1
)

REM Проверка наличия .env файла
if not exist .env (
    echo Создание примера .env файла...
    echo # Telegram Bot Token > .env.example
    echo BOT_TOKEN=your_bot_token_here >> .env.example
    echo. >> .env.example
    echo # PostgreSQL connection parameters >> .env.example
    echo DB_HOST=localhost >> .env.example
    echo DB_PORT=5432 >> .env.example
    echo DB_NAME=telegram_parser >> .env.example
    echo DB_USER=postgres >> .env.example
    echo DB_PASSWORD=password >> .env.example
    echo. >> .env.example
    echo # Target channel ID for forwarding messages >> .env.example
    echo TARGET_CHANNEL_ID=your_target_channel_id >> .env.example
    echo. >> .env.example
    echo # Checking interval in minutes >> .env.example
    echo CHECK_INTERVAL=3 >> .env.example
    echo. >> .env.example
    echo # Telethon API settings (для доступа к каналам без бота) >> .env.example
    echo # Получите данные на https://my.telegram.org/apps >> .env.example
    echo TELEGRAM_API_ID= >> .env.example
    echo TELEGRAM_API_HASH= >> .env.example
    echo TELEGRAM_PHONE= >> .env.example
    
    echo Создан файл .env.example. Переименуйте его в .env и настройте параметры.
)

echo.
echo Установка завершена успешно!
echo Для запуска бота используйте: start_bot.bat
echo.
echo ВАЖНО: Не забудьте создать файл .env на основе .env.example и заполнить в нем необходимые данные!
echo.
pause 