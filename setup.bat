@echo off
title Noest Cost Bot — تثبيت
cd /d "%~dp0"
echo ====================================
echo   Noest Cost Bot — تثبيت البوت
echo ====================================
echo.

REM تحقق من Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python غير مثبت. حمله من: https://www.python.org/downloads/
    echo    لا تنسى تحديد "Add Python to PATH" عند التثبيت
    pause
    exit /b 1
)

echo ✅ Python مثبت
echo.

REM تثبيت الحزم
echo جاري تثبيت الحزم المطلوبة...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ فشل تثبيت الحزم
    pause
    exit /b 1
)
echo ✅ تم تثبيت الحزم
echo.

REM التحقق من ملف .env
if not exist ".env" (
    echo ⚠️  ملف .env غير موجود.
    echo    انسخ .env.example إلى .env واملأ المعلومات
    copy .env.example .env >nul
    echo.
    echo    افتح .env بالمفكرة وضع التوكنات الصحيحة
)
echo.
echo ====================================
echo   ✅ التثبيت كامل
echo   شغل run.bat لتشغيل البوت
echo ====================================
pause
