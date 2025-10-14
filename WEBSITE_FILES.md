# 📦 ملفات الموقع للرفع - بوت سكرو

## ✅ **الملفات المطلوبة للموقع فقط:**

### 🌐 **ملفات الـ Frontend:**
- ✅ `index.html` - الصفحة الرئيسية
- ✅ `dashboard.html` - لوحة التحكم
- ✅ `login.html` - صفحة تسجيل الدخول (اختيارية)
- ✅ `styles.css` - ملف التصميم
- ✅ `script.js` - منطق الموقع
- ✅ `skro.png` - لوجو البوت

### ⚙️ **ملفات الـ Backend:**
- ✅ `backend.py` - خادم Flask
- ✅ `requirements.txt` - مكتبات Python

### 🚀 **ملفات الـ Deployment:**
- ✅ `Procfile` - أوامر التشغيل
- ✅ `railway.json` - إعدادات Railway
- ✅ `.gitignore` - ملفات لا ترفع
- ✅ `.env.example` - مثال للمتغيرات

### 📄 **ملفات البيانات:**
- ✅ `data/points.json` - النقاط والإحصائيات
- ✅ `data/vip_members.json` - أعضاء VIP
- ✅ `data/owner_config.json` - إعدادات الأونرز
- ✅ `data/servers.json` - عدد السيرفرات
- ✅ `data/referrals.json` - نظام الإحالة

### 📚 **ملفات التوثيق:**
- ✅ `README.md` - دليل المشروع
- ✅ `DEPLOYMENT_GUIDE.md` - دليل الرفع
- ✅ `QUICK_DEPLOY.md` - خطوات سريعة

---

## ❌ **الملفات اللي مش محتاجها للموقع:**

### 🤖 **ملفات البوت:**
- ❌ `Untitled-1.py` - البوت نفسه
- ❌ `token.txt` - توكن البوت
- ❌ `screw_bot.log` - لوجات البوت
- ❌ `import os.py` - ملفات البوت

### 📁 **مجلدات البوت:**
- ❌ `كروت سكرو/` - المجلد الأصلي (استخدمنا `data/` بدلاً منه)
- ❌ `.venv/` - البيئة الافتراضية
- ❌ `.vscode/` - إعدادات المحرر

### 🧪 **ملفات الاختبار:**
- ❌ `test_oauth.html` - صفحة اختبار
- ❌ `oauth_guide.html` - دليل OAuth
- ❌ `vip_test.html` - اختبار VIP
- ❌ `styles_Version*.css` - إصدارات قديمة

---

## 📋 **structure الموقع النهائي:**

```
📁 bot-screw-website/
├── 🌐 Frontend
│   ├── index.html
│   ├── dashboard.html
│   ├── styles.css
│   ├── script.js
│   └── skro.png
│
├── ⚙️ Backend  
│   ├── backend.py
│   └── requirements.txt
│
├── 🚀 Deployment
│   ├── Procfile
│   ├── railway.json
│   ├── .gitignore
│   └── .env.example
│
├── 📄 Data
│   └── data/
│       ├── points.json
│       ├── vip_members.json
│       ├── owner_config.json
│       ├── servers.json
│       └── referrals.json
│
└── 📚 Docs
    ├── README.md
    ├── DEPLOYMENT_GUIDE.md
    └── QUICK_DEPLOY.md
```

---

## 🔄 **كيف يتواصل مع البوت؟**

### الطريقة الحالية:
- الموقع يقرأ من `data/` folder
- البوت يكتب في `كروت سكرو/` folder
- **المشكلة**: البيانات مش متزامنة

### الحلول:
1. **نسخ البيانات يدوياً** كل فترة
2. **استخدام قاعدة بيانات مشتركة** (MySQL/PostgreSQL)
3. **عمل API** في البوت والموقع يستدعيه
4. **استخدام Cloud Storage** (Google Drive API)

---

## 🎯 **الخطوات التالية:**

1. ✅ **البيانات منفصلة** - تم
2. ✅ **الموقع يشتغل لوحده** - تم  
3. 🔄 **رفع الموقع** - التالي
4. ⏭️ **البوت في مكان منفصل** - لاحقاً
5. ⏭️ **ربط أفضل بينهم** - مستقبلاً

**دلوقتي الموقع جاهز للرفع بدون البوت! 🚀**