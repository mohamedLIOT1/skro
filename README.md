# 🎮 بوت سكرو - الموقع الرسمي

موقع ويب تفاعلي لبوت سكرو على Discord مع لوحة تحكم شخصية ونظام VIP.

## ✨ المميزات

### 🌐 **الموقع:**
- تصميم عربي متجاوب مع كل الشاشات
- صفحة رئيسية مع معلومات البوت
- لوحة تحكم شخصية للمستخدمين
- تسجيل دخول آمن عبر Discord OAuth2

### 👑 **نظام VIP:**
- ترحيب مميز للأعضاء المميزين
- شارات خاصة (Diamond, Gold, Silver)
- ترحيب خاص للمطورين والأونرز
- إحصائيات مفصلة للأعضاء المميزين

### 📊 **لوحة التحكم:**
- عرض النقاط والانتصارات
- تحويل النقاط إلى كريدتس
- نظام الإحالة والمكافآت
- شراء التراخيص المميزة

## 🚀 التشغيل المحلي

### المتطلبات:
- Python 3.8+
- Flask
- المكتبات في `requirements.txt`

### خطوات التشغيل:
```bash
# تثبيت المكتبات
pip install -r requirements.txt

# إعداد متغيرات البيئة
cp .env.example .env
# عدل .env بمعلومات Discord الخاصة بك

# تشغيل الخادم
python backend.py
```

الموقع هايفتح على: http://localhost:5000

## 🔧 إعداد Discord OAuth

1. اذهب إلى [Discord Developer Portal](https://discord.com/developers/applications)
2. أنشئ تطبيق جديد أو اختر الموجود
3. في OAuth2 → Redirects، أضف:
   ```
   http://localhost:5000/auth/discord/callback
   ```
4. انسخ Client ID و Client Secret
5. ضعهما في ملف `.env`

## 📁 الملفات المهمة

- `index.html` - الموقع الرئيسي
- `backend.py` - خادم Flask والـ APIs
- `script.js` - منطق الموقع
- `styles.css` - تصميم الموقع
- `.env` - إعدادات المتغيرات (لا ترفعه على Git!)
- `test_oauth.html` - صفحة اختبار OAuth

## 🎯 المميزات

### ✅ تم التنفيذ:
- موقع عربي كامل مع تصميم احترافي
- تسجيل دخول عبر Discord OAuth2
- لوحة تحكم تعرض النقاط والإحصائيات
- تحويل النقاط إلى كريدتس (10 نقاط = 1 كريدت)
- أوامر خاصة للأعضاء المميزين
- عدد السيرفرات الحقيقي
- نظام الإحالة (API جاهز)

## 🔌 APIs المتاحة

```
GET  /health                     - فحص الحالة
GET  /api/stats                  - إحصائيات عامة
GET  /api/user/<id>/points       - نقاط مستخدم معين
GET  /api/user/<id>/license      - حالة الترخيص
POST /api/user/<id>/purchase     - شراء ترخيص
POST /api/referral              - نظام الإحالة
GET  /auth/discord/login        - تسجيل دخول Discord
GET  /auth/discord/callback     - معالجة OAuth
GET  /api/auth/me               - معلومات المستخدم الحالي
GET  /auth/logout               - تسجيل خروج
```

## 🛠️ أوامر البوت الجديدة المقترحة

### أمر الإحالة (محتاج إضافة للبوت):
```python
@commands.command(name='سكرووو_صاحب_صحبو')
async def invite_friend(self, ctx, friend: discord.Member):
    # منطق الإحالة
    pass
```

## 🐛 حل المشاكل الشائعة

### الموقع لا يفتح:
1. تأكد من تشغيل `start_server.bat`
2. تأكد من عدم استخدام البورت 5000 بواسطة برنامج آخر
3. جرب: http://127.0.0.1:5000 بدلاً من localhost

### OAuth لا يعمل:
1. تأكد من إعدادات Discord Developer Portal
2. تأكد من ملف `.env` وأن CLIENT_SECRET صحيح
3. تأكد من REDIRECT_URI مطابق تماماً

### النقاط لا تظهر:
1. تأكد من وجود ملفات JSON في مجلد "كروت سكرو"
2. تأكد من صحة بيانات البوت في الملفات

---

## 🗃️ هيكل البيانات

```
📁 data/
├── points.json      # نقاط وإحصائيات المستخدمين
├── vip_members.json # أعضاء VIP وتصنيفاتهم
├── owner_config.json # معرفات المطورين/الأونرز
├── servers.json     # عدد السيرفرات
└── referrals.json   # نظام الإحالة
```

## 🔒 الأمان

- لا ترفع ملف `.env` على GitHub
- احتفظ بنسخة آمنة من الـ secrets
- استخدم HTTPS في الإنتاج
- راجع `.gitignore` قبل الرفع

## 📱 التقنيات المستخدمة

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Authentication**: Discord OAuth2
- **Styling**: RTL CSS مع دعم العربية
- **Deployment**: Railway/Render Ready

## 🚀 النشر (Deployment)

اقرأ `DEPLOYMENT_GUIDE.md` للتعليمات الكاملة، أو `QUICK_DEPLOY.md` للخطوات السريعة.

## 👥 المساهمة

هذا المشروع مفتوح المصدر، مرحب بالمساهمات والاقتراحات!

---

**🎮 تم تطويره بواسطة فريق بوت سكرو**