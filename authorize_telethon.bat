@echo off
echo Запуск авторизации Telethon клиента...
echo.

REM Проверяем наличие виртуального окружения
if exist .venv\Scripts\activate.bat (
    echo Активируем виртуальное окружение...
    call .venv\Scripts\activate.bat
) else (
    echo Виртуальное окружение не найдено. Используем системный Python.
)

REM Запускаем скрипт авторизации
python authorize_telethon.py

echo.
echo Нажмите любую клавишу для выхода...
pause > nul 