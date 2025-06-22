@echo off
echo Запуск Telegram бота для парсинга сообщений...
echo.

REM Активация виртуального окружения
call .venv\Scripts\activate.bat

REM Запуск бота
python keyboard_bot.py

REM В случае ошибки остановить выполнение
if %ERRORLEVEL% neq 0 (
    echo.
    echo Произошла ошибка при запуске бота.
    echo Нажмите любую клавишу для выхода...
    pause > nul
) 