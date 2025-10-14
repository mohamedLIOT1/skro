@echo off
title بوت سكرو - خادم الويب
echo 🎮 جاري تشغيل خادم بوت سكرو...
echo.

cd /d "%~dp0"

REM Check if Python is available
"C:/Users/mm312/AppData/Local/Programs/Python/Python312/python.exe" --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ خطأ: Python غير موجود في المسار المحدد
    echo يرجى التأكد من تثبيت Python 3.12
    pause
    exit /b 1
)

echo ✅ تم العثور على Python
echo 🚀 جاري تشغيل الخادم...
echo.
echo 📍 الموقع متاح على: http://localhost:5000
echo 🔗 صفحة الاختبار: http://localhost:5000/test_oauth.html
echo.
echo 💡 اضغط Ctrl+C لإيقاف الخادم
echo ================================
echo.

"C:/Users/mm312/AppData/Local/Programs/Python/Python312/python.exe" backend.py

pause