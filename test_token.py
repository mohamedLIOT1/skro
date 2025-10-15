#!/usr/bin/env python3
"""
اختبار التوكن للتأكد من صحته
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

bot_token = os.environ.get('DISCORD_BOT_TOKEN')

if not bot_token:
    print("❌ لم يتم العثور على DISCORD_BOT_TOKEN في ملف .env")
    exit(1)

print(f"🔍 اختبار التوكن: {bot_token[:30]}...")

# اختبار 1: جلب معلومات البوت نفسه
print("\n📋 اختبار 1: جلب معلومات البوت...")
try:
    headers = {'Authorization': f'Bot {bot_token}'}
    resp = requests.get('https://discord.com/api/v10/users/@me', headers=headers)
    
    if resp.status_code == 200:
        bot_data = resp.json()
        print(f"✅ التوكن يعمل بشكل صحيح!")
        print(f"   اسم البوت: {bot_data.get('username')}")
        print(f"   معرف البوت: {bot_data.get('id')}")
        print(f"   البوت: {bot_data.get('bot', False)}")
    elif resp.status_code == 401:
        print(f"❌ التوكن غير صحيح أو منتهي الصلاحية")
        print(f"   الرد: {resp.text}")
    else:
        print(f"⚠️ خطأ غير متوقع: {resp.status_code}")
        print(f"   الرد: {resp.text}")
except Exception as e:
    print(f"❌ خطأ في الاتصال: {e}")

# اختبار 2: جلب معلومات مستخدم حقيقي
print("\n📋 اختبار 2: جلب معلومات مستخدم من Discord...")
test_user_id = "1064878296480895006"  # أول user_id من points.json
try:
    headers = {'Authorization': f'Bot {bot_token}'}
    resp = requests.get(f'https://discord.com/api/v10/users/{test_user_id}', headers=headers)
    
    if resp.status_code == 200:
        user_data = resp.json()
        print(f"✅ تم جلب بيانات المستخدم بنجاح!")
        print(f"   الاسم: {user_data.get('username')}")
        print(f"   الاسم العالمي: {user_data.get('global_name')}")
        print(f"   معرف الصورة: {user_data.get('avatar')}")
        if user_data.get('avatar'):
            avatar_url = f"https://cdn.discordapp.com/avatars/{test_user_id}/{user_data.get('avatar')}.png?size=256"
            print(f"   رابط الصورة: {avatar_url}")
    elif resp.status_code == 401:
        print(f"❌ التوكن غير صحيح")
    elif resp.status_code == 403:
        print(f"⚠️ البوت لا يملك صلاحية لجلب بيانات المستخدم")
        print(f"   تأكد من أن البوت في نفس السيرفر مع المستخدم")
    elif resp.status_code == 404:
        print(f"⚠️ المستخدم غير موجود أو معرفه خطأ")
    else:
        print(f"⚠️ خطأ: {resp.status_code}")
        print(f"   الرد: {resp.text}")
except Exception as e:
    print(f"❌ خطأ في الاتصال: {e}")

print("\n" + "="*50)
print("انتهى الاختبار!")
