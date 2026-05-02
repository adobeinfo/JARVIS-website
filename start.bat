@echo off
chcp 65001 >nul
title JARVIS Website
color 0A
cls
echo.
echo  ================================================
echo   JARVIS AI - Запуск веб-сайта
echo  ================================================
echo.
echo  Адрес: http://localhost:5000
echo  Админка: http://localhost:5000/admin
echo  Логин: admin / jarvis2024
echo.
echo  Закройте это окно чтобы остановить сервер
echo  ================================================
echo.
cd /d "%~dp0"
python server.py
pause
