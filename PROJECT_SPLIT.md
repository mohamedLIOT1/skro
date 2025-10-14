# 🗂️ تقسيم المشروع - بوت سكرو

## 📊 **المشروع الحالي**
```
📁 New folder (2)/
├── 🌐 الموقع (Website)
│   ├── index.html
│   ├── dashboard.html  
│   ├── styles.css
│   ├── script.js
│   ├── backend.py
│   ├── .env
│   ├── requirements.txt
│   └── ملفات الـ deployment
│
└── 📁 كروت سكرو/
    ├── 🤖 البوت (Discord Bot)
    │   ├── Untitled-1.py
    │   ├── token.txt
    │   └── ملفات أخرى للبوت
    │
    └── 📄 البيانات المشتركة
        ├── points.json
        ├── vip_members.json
        ├── owner_config.json
        └── referrals.json
```

---

## ✂️ **التقسيم المقترح**

### 🌐 **مشروع الموقع فقط:**
```
📁 bot-screw-website/
├── index.html
├── dashboard.html
├── login.html
├── styles.css
├── script.js
├── backend.py
├── .env
├── requirements.txt
├── Procfile
├── railway.json
├── .gitignore
└── 📁 data/ (نسخة من ملفات JSON)
    ├── points.json
    ├── vip_members.json
    ├── owner_config.json
    └── servers.json
```

### 🤖 **مشروع البوت فقط:**
```
📁 screw-discord-bot/
├── bot.py (Untitled-1.py مغير الاسم)
├── token.txt
├── requirements.txt
└── 📁 data/
    ├── points.json
    ├── vip_members.json
    ├── owner_config.json
    └── referrals.json
```

---

## 🔧 **خطوات التقسيم**

### 1️⃣ **إنشاء مجلد الموقع:**
```bash
mkdir bot-screw-website
cd bot-screw-website
```

### 2️⃣ **نسخ ملفات الموقع:**
- `index.html`
- `dashboard.html` 
- `styles.css`
- `script.js`
- `backend.py`
- `.env`
- `requirements.txt`
- `Procfile`
- `railway.json`
- `.gitignore`

### 3️⃣ **إنشاء مجلد البيانات:**
```bash
mkdir data
# نسخ ملفات JSON من "كروت سكرو"
```

### 4️⃣ **تعديل المسارات في backend.py:**
```python
# من:
DATA_DIR = os.path.join(BASE_DIR, 'كروت سكرو')

# إلى:
DATA_DIR = os.path.join(BASE_DIR, 'data')
```

---

## 🚀 **مميزات التقسيم**

### للموقع:
✅ **أسرع في الرفع** - ملفات أقل  
✅ **أبسط في الإدارة** - مش محتاج ملفات البوت  
✅ **أأمن** - مفيش tokens في الموقع  
✅ **أسهل في التطوير** - تركيز على الـ web فقط  

### للبوت:
✅ **استقلالية كاملة** - يشتغل في أي مكان  
✅ **حماية أكبر** - Token مش معرض للـ web  
✅ **سهولة الصيانة** - تحديثات منفصلة  

---

## 🔄 **التواصل بينهم**

### الطريقة الحالية (مؤقتة):
- الموقع يقرأ من ملفات JSON محلية
- البوت يكتب في ملفات JSON منفصلة
- **المشكلة**: البيانات مش متزامنة

### الحل المقترح (للمستقبل):
```python
# في البوت - إضافة API endpoint
@bot.event
async def on_ready():
    app = Flask(__name__)
    
    @app.route('/api/bot-stats')
    def bot_stats():
        return jsonify({
            'servers': len(bot.guilds),
            'users': len(bot.users)
        })
    
    app.run(host='0.0.0.0', port=3001)
```

```javascript
// في الموقع - استدعاء API البوت
async function updateBotStats() {
    const response = await fetch('http://bot-server:3001/api/bot-stats');
    const data = await response.json();
    // تحديث الإحصائيات
}
```

---

## 📋 **الخطوات العملية دلوقتي**

### 1. **إنشاء مجلد جديد للموقع**
### 2. **نسخ الملفات المطلوبة بس** 
### 3. **تعديل المسارات**
### 4. **رفع الموقع لوحده**
### 5. **البوت يفضل في مكانه**

---

**عاوز أساعدك تعمل التقسيم ده دلوقتي؟** 🛠️