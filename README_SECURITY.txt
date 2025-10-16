دليل حماية موقع skro
====================

1. جميع الأسرار (التوكنات، المفاتيح) يجب أن تكون في ملف .env فقط، ولا يتم رفعه أبدًا.
2. تأكد أن مجلد data/ وملفات json و .env ليست في مجلد يمكن الوصول له من الإنترنت.
3. استخدم chmod 600 .env data/*.json على السيرفر.
4. لتفعيل النسخ الاحتياطي التلقائي:
   - أضف سكريبت بايثون أو cron:
     cp -r data data_backup_$(date +%F)
5. راقب اللوجات باستمرار لأي نشاط غريب.
6. حدّث جميع المكتبات كل فترة:
   pip install --upgrade flask requests jwt flask-cors flask-seasurf bleach python-dotenv flask-limiter
7. استخدم Cloudflare أو WAF إذا كان متاحًا.
