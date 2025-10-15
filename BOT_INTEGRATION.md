# Bot Integration Guide (Discord.py)

This guide shows how to keep the website in sync with your bot for VIP tiers, points, and servers count, and how to prevent self-awarded points.

## 1. Install requirements in your bot

```bash
pip install aiohttp
```

## 2. Add the helper
Copy `bot_sync_helper.py` from this repo into your bot project and adjust:
- API_BASE (your website URL)
- API_KEY (must match backend VIP_API_KEY)

## 3. Use it in your bot

```python
import aiohttp
from bot_sync_helper import WebsiteSyncClient

sync = WebsiteSyncClient()

@bot.event
async def on_ready():
    # Report servers count
    session = aiohttp.ClientSession()
    sync.attach_session(session)
    await sync.set_servers(len(bot.guilds))

@bot.event
async def on_guild_join(guild):
    await sync.set_servers(len(bot.guilds))

@bot.event
async def on_guild_remove(guild):
    await sync.set_servers(len(bot.guilds))

# Example command: award points after a game
@bot.command()
async def win(ctx, points: int = 10, score: int = 0):
    # Prevent self-award exploit: allow only in context of game/referee role/permission
    if not ctx.author.guild_permissions.manage_guild and ctx.author.id not in [OWNER_IDs]:
        await ctx.send("❌ ليس لديك صلاحية لتعديل النقاط.")
        return
    await sync.update_points(ctx.guild.id, ctx.author.id, points=points, games=1, score=score, mode="inc")
    await ctx.send(f"✅ تم إضافة {points} نقطة!")

# Example: set VIP
@bot.command()
async def setvip(ctx, member: discord.Member, tier: str):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("❌ تحتاج صلاحية الأدمن.")
    tier = tier.capitalize()
    if tier not in ("Diamond", "Gold", "Silver"):
        return await ctx.send("❌ اختر: Diamond | Gold | Silver")
    await sync.set_vip(member.id, tier)
    await ctx.send(f"✅ {member.mention} أصبح VIP {tier}")

# Example: remove VIP
@bot.command()
async def unvip(ctx, member: discord.Member):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("❌ تحتاج صلاحية الأدمن.")
    await sync.set_vip(member.id, None)
    await ctx.send(f"✅ تم إزالة VIP من {member.mention}")
```

## 4. Prevent self-awarded points properly
- لا تسمح بأوامر تعديل النقاط إلا لذوي صلاحيات (administrator/manage_guild) أو في قنوات/أحداث اللعبة فقط.
- استخدم منطق اللعبة ليحسب النقاط تلقائياً بدل إدخال المستخدم نقاط لنفسه.
- راقب الأنشطة غير الطبيعية وسجلها في لوج.

## 5. Configure the API key securely
- Change `VIP_API_KEY` in backend (env var) and `API_KEY` in bot to a strong secret.
- Avoid committing real secrets to public repos.

## 6. Dashboard effects
- Once the endpoints are called, the website updates immediately because it reads from JSON files directly.
