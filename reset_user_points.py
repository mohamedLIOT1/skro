#!/usr/bin/env python3
"""
سكريبت لتصفير نقاط مستخدم معين
"""
import requests

# إعدادات
USER_ID = 1064878296480895006
GUILD_ID = "1193821158265589852"
API_KEY = "skro_vip_api_key_change_me"
API_URL = "https://www.grevo.ct.ws/points/update"

def reset_user_points(user_id, guild_id):
    """تصفير نقاط المستخدم"""
    print(f"🔄 جاري تصفير نقاط المستخدم {user_id}...")
    
    response = requests.post(
        API_URL,
        headers={'X-API-Key': API_KEY},
        json={
            'user_id': str(user_id),
            'guild_id': str(guild_id),
            'mode': 'set',  # وضع التعيين المباشر
            'points': 0,
            'wins': 0,
            'games': 0,
            'best': 0,
            'total_score': 0
        },
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ تم تصفير النقاط بنجاح!")
        print(f"📊 البيانات الجديدة:")
        print(f"   - النقاط: {data['entry']['points']}")
        print(f"   - الانتصارات: {data['entry']['wins']}")
        print(f"   - الألعاب: {data['entry']['games']}")
        return True
    else:
        print(f"❌ فشل التصفير: {response.status_code}")
        print(f"   الخطأ: {response.text}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🎮 سكريبت تصفير نقاط المستخدم")
    print("=" * 50)
    
    success = reset_user_points(USER_ID, GUILD_ID)
    
    if success:
        print("\n🔍 التحقق من النقاط الجديدة...")
        verify_response = requests.get(
            f"https://www.grevo.ct.ws/api/user/{USER_ID}/points",
            timeout=10
        )
        
        if verify_response.status_code == 200:
            stats = verify_response.json()['stats']
            print(f"✅ النقاط الحالية: {stats['points']}")
            print(f"✅ الكريدتس الحالية: {stats['credits']}")
        else:
            print(f"⚠️ تعذر التحقق من النقاط")
    
    print("\n" + "=" * 50)
