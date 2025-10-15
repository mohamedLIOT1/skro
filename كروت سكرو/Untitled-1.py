WEBHOOK_URL = "https://discord.com/api/webhooks/1428001538391150615/l17_9MiGYOMIU7mIdgJCoLm5jmsy24MDS7TCpqdCW1BDO_1uQt4VIUTRDy3SEsyfJ7k0"

# إرسال رسالة للويب هوك (نص فقط)
async def send_webhook_message(content):
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(WEBHOOK_URL, json={"content": content})
    except Exception as e:
        logger.error(f"Webhook send failed: {e}")
# سكرو Bot — النسخة النهائية الكاملة
import os
import json
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Select
import asyncio
import random
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import aiohttp
from bot_sync_helper import WebsiteSyncClient



# ===================
# تعريف deck_list (قائمة الكروت الأساسية)
# ===================
deck_list = [
    ("-1", 1),
    ("سكرو أخضر", 2),
    ("1", 4), ("2", 4), ("3", 4), ("4", 4), ("5", 4), ("6", 4),
    ("7", 4),
    ("8", 4),
    ("9", 4),
    ("10", 4),
    ("خد بس", 1),
    ("خد وهات", 4),
    ("سكرو أحمر", 2),
    ("+20", 3),
    ("كعب داير", 2),
    ("بصرة", 2),
    ("الحرامي", 1),
    ("see swap", 1),
    ("بينج", 2),
    ("بونج", 2),
    ("على كيفك", 2),
]

# ===================
# تعريف Lobby الأساسي (مبسط)
# ===================
class Lobby:
    # المتغيرات الخاصة بالـ AFK والسكيب يتم تهيئتها في __init__
    def __init__(self, channel, team_mode=False, vip_mode=False):
        self.channel = channel
        self.players = []
        self.deck = []
        self.ground = []
        self.hands = {}
        self.round_number = 1
        self.current_turn_player = None
        self.current_draw_active = False
        self.current_draw_view = None
        self.current_draw_msg = None
        self.scrap_player = None
        self.is_stopped = False
        self.join_view = None
        self.join_msg = None
        self.pending_interactions = set()
        self.teams = []
        # أنماط اللعبة
        self.vip_mode = vip_mode
        self.team_mode = team_mode
        self.teams_mode = team_mode  # alias للتوافق
        # إحصائيات
        self.players_viewed_cards = set()
        self.scores = {}
        self.started = False
        self.owner = None
        self.join_message = None
        self.active = True
        self.afk_counter = {}  # عداد AFK لكل لاعب
        self._skip_next_turn = False  # سكيب الدور القادم (بينج/بونج)
        # أضف أي متغيرات أخرى حسب الحاجة
    
    def cleanup_lobby(self):
        """تنظيف موارد اللوبي"""
        try:
            if self.join_view:
                self.join_view.stop()
            if self.current_draw_view:
                self.current_draw_view.stop()
            self.pending_interactions.clear()
        except Exception:
            pass

# ===================
# إعداد نظام التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('screw_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ScrewBot')

# --- Website Sync Client (VIP/Points/Servers) ---
sync_client = WebsiteSyncClient()
aiohttp_session: Optional[aiohttp.ClientSession] = None

async def _init_sync_client():
    global aiohttp_session
    try:
        if aiohttp_session is None or aiohttp_session.closed:
            aiohttp_session = aiohttp.ClientSession()
        sync_client.attach_session(aiohttp_session)
    except Exception as e:
        logger.error(f"Failed to init WebsiteSyncClient: {e}")

async def _safe_call(coro, ctx: str = ""):
    try:
        return await coro
    except Exception as e:
        logger.error(f"Sync error [{ctx}]: {e}")
        return None

# اختيارياً: مزامنة فورية على سيرفر تطوير واحد (لتفادي انتظار نشر الأوامر عالمياً)
# ضع DEV_GUILD_ID كمتغير بيئة أو في ملف .env
try:
    DEV_GUILD_ID = int(os.getenv("DEV_GUILD_ID", "0") or "0")
except Exception:
    DEV_GUILD_ID = 0

############################################
# نظام تعريف الأونر (Owner System) — يدعم عدة أونرز
############################################
# ضع IDs لحسابات الأونرز الأساسية هنا (User IDs من Discord)
BASE_OWNER_IDS = {1064878296480895006, 510419036350185475}

# ملف تخزين الأونرز الديناميكيين
AUTO_OWNER_FILE = Path(__file__).parent / "owner_config.json"

def _normalize_owner_ids(raw) -> set[int]:
    ids = set()
    try:
        if isinstance(raw, (list, tuple, set)):
            ids = {int(x) for x in raw}
        elif raw is None:
            ids = set()
        else:
            # توافق مع الإصدارات القديمة: مفتاح مفرد
            ids = {int(raw)}
    except Exception:
        ids = set()
    return ids

def load_dynamic_owners() -> set[int]:
    """تحميل الأونرز المخزنين في الملف (قديماً كان owner_id مفرد)."""
    try:
        if AUTO_OWNER_FILE.exists():
            with open(AUTO_OWNER_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
            if 'owner_ids' in data:
                return _normalize_owner_ids(data.get('owner_ids'))
            # توافق: دعم المفتاح القديم 'owner_id'
            if 'owner_id' in data:
                return _normalize_owner_ids(data.get('owner_id'))
    except Exception:
        pass
    return set()

def save_dynamic_owners(owner_ids: set[int]) -> bool:
    """حفظ قائمة الأونرز الديناميكية (لا تشمل الأساسيين)."""
    try:
        to_save = sorted({int(x) for x in owner_ids})
        with open(AUTO_OWNER_FILE, 'w', encoding='utf-8') as f:
            json.dump({'owner_ids': to_save}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

# حالة الأونرز الحالية
DYNAMIC_OWNER_IDS: set[int] = load_dynamic_owners()

def all_owner_ids() -> set[int]:
    return set(BASE_OWNER_IDS) | set(DYNAMIC_OWNER_IDS)

# نظام VIP - ضع هنا IDs الأعضاء المميزين
VIP_MEMBERS = {
    # 123456789: "VIP Gold",  # مثال
    # 987654321: "VIP Diamond",
}

# أو لو تحب تخليه يقرأ من ملف
VIP_FILE = Path(__file__).parent / "vip_members.json"

def load_vip_members():
    """تحميل أعضاء VIP من ملف"""
    try:
        if VIP_FILE.exists():
            with open(VIP_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

def save_vip_members(vips: dict):
    """حفظ أعضاء VIP في ملف"""
    try:
        with open(VIP_FILE, 'w', encoding='utf-8') as f:
            json.dump(vips, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

# تحميل VIPs من الملف
VIP_MEMBERS.update(load_vip_members())

# ===================
# نظام شراء المودات (Purchases System)
# ===================
PURCHASES_FILE = Path(__file__).parent / "purchases.json"

def load_purchases():
    """تحميل المشتريات من ملف"""
    try:
        if PURCHASES_FILE.exists():
            with open(PURCHASES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

def save_purchases(purchases: dict):
    """حفظ المشتريات في ملف"""
    try:
        with open(PURCHASES_FILE, 'w', encoding='utf-8') as f:
            json.dump(purchases, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

# تحميل المشتريات من الملف
# الهيكل: {guild_id: {user_id: ["teams_mode", "other_mode"]}}
PURCHASES = load_purchases()

def has_purchased(guild_id: int, user_id: int, mode: str) -> bool:
    """التحقق من شراء مود معين"""
    try:
        guild_key = str(guild_id)
        user_key = str(user_id)
        if guild_key in PURCHASES:
            if user_key in PURCHASES[guild_key]:
                return mode in PURCHASES[guild_key][user_key]
        return False
    except Exception:
        return False

def add_purchase(guild_id: int, user_id: int, mode: str) -> bool:
    """إضافة مشترى جديد"""
    try:
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key not in PURCHASES:
            PURCHASES[guild_key] = {}
        if user_key not in PURCHASES[guild_key]:
            PURCHASES[guild_key][user_key] = []
        
        if mode not in PURCHASES[guild_key][user_key]:
            PURCHASES[guild_key][user_key].append(mode)
            save_purchases(PURCHASES)
            return True
        return False
    except Exception:
        return False

def is_owner(user: discord.abc.User) -> bool:
    """يتحقق إذا كان المستخدم ضمن قائمة الأونرز الحالية."""
    try:
        return int(getattr(user, 'id', 0)) in all_owner_ids()
    except Exception:
        return False

def is_vip(user: discord.abc.User) -> bool:
    """فحص إذا كان المستخدم VIP"""
    try:
        return int(getattr(user, 'id', 0)) in VIP_MEMBERS
    except Exception:
        return False

def get_vip_tier(user: discord.abc.User) -> str:
    """الحصول على درجة VIP للمستخدم"""
    try:
        user_id = int(getattr(user, 'id', 0))
        return VIP_MEMBERS.get(user_id, "")
    except Exception:
        return ""

def format_member(member: discord.Member) -> str:
    try:
        if is_owner(member):
            return f"{member.mention} 👑"
        elif is_vip(member):
            vip_tier = get_vip_tier(member)
            if "Diamond" in vip_tier:
                return f"{member.mention} 💎"
            elif "Gold" in vip_tier:
                return f"{member.mention} 🌟"
            elif "Silver" in vip_tier:
                return f"{member.mention} ⭐"
            else:
                return f"{member.mention} 🎖️"
        return f"{member.mention}"
    except Exception:
        return str(member)

def get_owner_embed_color(user: discord.abc.User) -> int:
    return 0xFFD700 if is_owner(user) else 0x3498db

def get_vip_embed_color(user: discord.abc.User) -> int:
    """ألوان مميزة لأعضاء VIP"""
    if is_owner(user):
        return 0xFFD700  # ذهبي للأونر
    elif is_vip(user):
        vip_tier = get_vip_tier(user)
        if "Diamond" in vip_tier:
            return 0xB9F2FF  # أزرق فاتح للدايموند
        elif "Gold" in vip_tier:
            return 0xFFD700  # ذهبي للذهب
        elif "Silver" in vip_tier:
            return 0xC0C0C0  # فضي للفضة
        else:
            return 0xFF69B4  # وردي للVIP العادي
    return 0x3498db

class PointsManager:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.data: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._load()

    def _load(self):
        try:
            if self.file_path.exists():
                with self.file_path.open("r", encoding="utf-8") as f:
                    self.data = json.load(f)
            else:
                self.data = {}
        except Exception:
            self.data = {}

    def _save(self):
        try:
            with self.file_path.open("w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _ensure_user(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        gkey = str(guild_id)
        ukey = str(user_id)
        if gkey not in self.data:
            self.data[gkey] = {}
        if ukey not in self.data[gkey]:
            self.data[gkey][ukey] = {
                "points": 0,
                "wins": 0,
                "games": 0,
                "best": None,
                "total_score": 0
            }
        return self.data[gkey][ukey]

    def get_user_stats(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        return self._ensure_user(guild_id, user_id)

    def add_points(self, guild_id: int, user_id: int, delta: int) -> Dict[str, Any]:
        stats = self._ensure_user(guild_id, user_id)
        stats["points"] = int(stats.get("points", 0)) + int(delta)
        self._save()
        return stats

    def record_game_result(self, guild_id: int, user_id: int, round_score: int, is_winner: bool):
        stats = self._ensure_user(guild_id, user_id)
        stats["games"] = int(stats.get("games", 0)) + 1
        stats["total_score"] = int(stats.get("total_score", 0)) + int(round_score)
        best = stats.get("best")
        try:
            if best is None:
                stats["best"] = int(round_score)
            else:
                stats["best"] = int(min(int(best), int(round_score)))
        except Exception:
            stats["best"] = int(round_score)
        if is_winner:
            stats["wins"] = int(stats.get("wins", 0)) + 1
        self._save()


POINTS_FILE = Path(__file__).parent / "points.json"
points_manager = PointsManager(POINTS_FILE)


# ===================
# تعريف البوت قبل أي أوامر سلاش
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# أوامر VIP (Prefix فقط)
@bot.command(name="vipadd")
async def cmd_vip_add(ctx, member: discord.Member, *, tier: str):
    """👑 إضافة عضو VIP — استخدام: !vipadd @member <VIP Diamond/Gold/Silver/Basic>"""
    if not is_owner(ctx.author):
        return await ctx.send("❌ هذا الأمر للأونر فقط", delete_after=5)
    VIP_MEMBERS[member.id] = tier
    save_vip_members(VIP_MEMBERS)
    try:
        await _init_sync_client()
        await _safe_call(sync_client.set_vip(member.id, tier), ctx=f"set_vip:add:{member.id}:{tier}")
    except Exception:
        pass
    await send_webhook_message(f"👑 تمت إضافة VIP: {member.display_name} - {tier} بواسطة {ctx.author.display_name}")
    icon = "💎" if "Diamond" in tier else "🌟" if "Gold" in tier else "⭐" if "Silver" in tier else "🎖️"
    embed = discord.Embed(title=f"{icon} تم منح VIP!", description=f"{format_member(member)} أصبح {tier}")
    await ctx.send(embed=embed)

@bot.command(name="vipremove")
async def cmd_vip_remove(ctx, member: discord.Member):
    """👑 إزالة عضو VIP — استخدام: !vipremove @member"""
    if not is_owner(ctx.author):
        return await ctx.send("❌ هذا الأمر للأونر فقط", delete_after=5)
    if member.id not in VIP_MEMBERS:
        return await ctx.send("❌ ليس VIP", delete_after=5)
    old_tier = VIP_MEMBERS.pop(member.id)
    save_vip_members(VIP_MEMBERS)
    try:
        await _init_sync_client()
        await _safe_call(sync_client.set_vip(member.id, None), ctx=f"set_vip:remove:{member.id}")
    except Exception:
        pass
    await send_webhook_message(f"❌ تم إزالة VIP: {member.display_name} بواسطة {ctx.author.display_name}")
    embed = discord.Embed(title="❌ تم إلغاء VIP", description=f"{format_member(member)} لم يعد {old_tier}")
    await ctx.send(embed=embed)

@bot.command(name="viplist")
async def cmd_vip_list(ctx):
    """👑 عرض قائمة أعضاء VIP — استخدام: !viplist"""
    if not is_owner(ctx.author):
        return await ctx.send("❌ هذا الأمر للأونر فقط", delete_after=5)
    if not VIP_MEMBERS:
        return await ctx.send("لا يوجد أعضاء VIP حالياً", delete_after=10)
    embed = discord.Embed(title="📋 قائمة أعضاء VIP", color=0xFFD700)
    lines = []
    for user_id, tier in VIP_MEMBERS.items():
        icon = "💎" if "Diamond" in tier else "🌟" if "Gold" in tier else "⭐" if "Silver" in tier else "🎖️"
        name = None
        try:
            user = ctx.guild.get_member(int(user_id)) if ctx.guild else None
            if not user and ctx.guild:
                user = await ctx.guild.fetch_member(int(user_id))
            name = user.display_name if user else f"User {user_id}"
        except Exception:
            name = f"User {user_id}"
        lines.append(f"{icon} **{name}** - {tier}")
    embed.description = "\n".join(lines)
    await ctx.send(embed=embed)

@bot.command(name="vipcheck")
async def cmd_vip_check(ctx, member: discord.Member):
    """👑 فحص حالة VIP — استخدام: !vipcheck @member"""
    tier = get_vip_tier(member) if is_vip(member) else None
    if tier:
        icon = "💎" if "Diamond" in tier else "🌟" if "Gold" in tier else "⭐" if "Silver" in tier else "🎖️"
        embed = discord.Embed(title=f"{icon} عضو VIP", description=f"{member.display_name} هو {tier}", color=get_vip_embed_color(member))
    else:
        embed = discord.Embed(title="👤 عضو عادي", description=f"{member.display_name} ليس VIP", color=0x95a5a6)
    await ctx.send(embed=embed)

active_lobbies = {}

@bot.command(name="vipmode")
@commands.guild_only()
async def cmd_vipmode(ctx):
    """ابدأ غرفة لعب VIP فقط — استخدام: !vipmode"""
    if ctx.channel.id in active_lobbies:
        await ctx.send("❌ هناك لعبة نشطة بالفعل في هذه الغرفة!", delete_after=5)
        return
    if not is_vip(ctx.author):
        await ctx.send("❌ هذا المود حصري لأعضاء VIP فقط!", delete_after=5)
        return
    lobby = Lobby(ctx.channel)
    lobby.vip_mode = True
    active_lobbies[ctx.channel.id] = lobby

    view = JoinView(lobby, msg_holder={})
    embed = generate_lobby_embed(lobby, countdown=20)
    msg = await ctx.send(embed=embed, view=view)
    await send_webhook_message(f"🚪 تم فتح غرفة VIP بواسطة {ctx.author.display_name} في {ctx.channel.name}")

    for i in range(20, 0, -1):
        await asyncio.sleep(1)
        try:
            await msg.edit(embed=generate_lobby_embed(lobby, countdown=i), view=view)
        except Exception:
            pass

    try:
        view.stop()
        final_embed = discord.Embed(title="⏰ انتهى وقت الانضمام", description="**انتهى وقت الانضمام للـ VIP**", color=0xf39c12)
        await msg.edit(embed=final_embed, view=None)
    except Exception:
        pass

    if len(lobby.players) < 2:
        await ctx.send("❌ يحتاج على الأقل لاعبين 2 للبدء!")
        active_lobbies.pop(ctx.channel.id, None)
        return

    lobby.deck = create_full_deck()
    deal_hands(lobby)
    await start_round(ctx.channel, lobby)

def create_full_deck(team_mode=False):
    full = []
    if team_mode:
        # مود التيمات: deck خاص
        team_deck = [
            ("بينج", 2),
            ("بونج", 2),
            ("على كيفك", 2),
        ]
        # باقي الكروت (بدون الحرامي وبدون كروت التيمات لتفادي التكرار)
        team_cards = {"بينج", "بونج", "على كيفك"}
        for card, count in deck_list:
            if card == "الحرامي" or card in team_cards:
                continue
            full.extend([card] * count)
        for card, count in team_deck:
            full.extend([card] * count)
    else:
        # مود سكرووو العادي: استبعاد بينج/بونج/على كيفك
        blacklist = {"بينج", "بونج", "على كيفك"}
        for card, count in deck_list:
            if card in blacklist:
                continue
            full.extend([card] * count)
    random.shuffle(full)
    return full

def deal_hands(lobby: Lobby):
    try:
        hands = {}
        if not lobby or not lobby.players:
            logger.error("Cannot deal hands: invalid lobby or no players")
            return {}
        
        # التأكد من وجود ديك كافي
        cards_needed = len(lobby.players) * 4
        if not lobby.deck:
            logger.error("Deck is empty!")
            return {}
        
        if len(lobby.deck) < cards_needed:
            logger.warning(f"Insufficient cards in deck: {len(lobby.deck)} cards for {len(lobby.players)} players (need {cards_needed})")
            # نحاول نعبي الديك من الأرض لو ممكن
            if lobby.ground and len(lobby.ground) > 1:
                refill_deck_from_ground(lobby)
        
        for player in lobby.players:
            hands[player] = []
            for _ in range(4):
                if lobby.deck:
                    card = lobby.deck.pop()
                    hands[player].append(card)
                else:
                    logger.warning(f"Deck empty while dealing to {player.display_name}")
                    break
        
        lobby.hands = hands
        
        # تهيئة النقاط لكل لاعب
        for p in lobby.players:
            lobby.scores.setdefault(p, 0)
        
        logger.info(f"✅ Dealt hands to {len(lobby.players)} players, {len(lobby.deck)} cards remaining in deck")
        return hands
    except Exception as e:
        logger.error(f"❌ Error dealing hands: {str(e)}")
        return {}

def generate_lobby_embed(lobby: Lobby, countdown: int = None):
    embed = discord.Embed(
        title="🎮 غرفة لعبة سكرو",
        description="**انضم الآن وابدأ المغامرة!** 🚀",
        color=0x9b59b6
    )
    
    if lobby.players:
        players_text = ""
        for idx, p in enumerate(lobby.players, start=1):
            players_text += f"{idx}. {format_member(p)}\n"
        embed.add_field(
            name=f"👥 اللاعبين المنضمين ({len(lobby.players)}/8)",
            value=players_text,
            inline=False
        )
    else:
        embed.add_field(
            name="👥 اللاعبين المنضمين",
            value="*لا يوجد لاعبين بعد... كن أول المنضمين!* 🎯",
            inline=False
        )
    
    if countdown is not None:
        if countdown == 0:
            embed.set_footer(text="⏰ انتهى وقت الانضمام | ابدأ اللعب!")
            embed.color = 0xe74c3c
        else:
            embed.set_footer(text=f"⏳ اللعبة تبدأ بعد {countdown} ثانية...")
            embed.color = 0xf39c12
    
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1303340209575825449/1425772990091755581/Untitled_design_1.png?ex=68e8ce12&is=68e77c92&hm=591d466fc5ec896fc564ae467ec1b4cc361067f6ccd7ee11a220a1f0e7b6ebc0")
    return embed

def refill_deck_from_ground(lobby: Lobby):
    try:
        if not lobby or not hasattr(lobby, 'ground') or not lobby.ground:
            logger.warning("Cannot refill deck: no ground cards available")
            return False
        
        if len(lobby.ground) <= 1:
            logger.warning("Cannot refill deck: insufficient ground cards")
            return False
        
        cards_before = len(lobby.deck) if lobby.deck else 0
        to_shuffle = lobby.ground[:-1]
        random.shuffle(to_shuffle)
        
        if not lobby.deck:
            lobby.deck = []
        lobby.deck.extend(to_shuffle)
        
        last = lobby.ground[-1]
        lobby.ground = [last]
        
        logger.info(f"Refilled deck: {cards_before} -> {len(lobby.deck)} cards, {len(to_shuffle)} from ground")
        return True
    except Exception as e:
        logger.error(f"Error refilling deck from ground: {str(e)}")
        return False

def card_key(card_str: str):
    return str(card_str).split("\n")[0].strip()

CARD_POINT_VALUES = {
    "-1": -1, "سكرو أخضر": 0,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "7": 7, "8": 8, "9": 9, "10": 10,
    "خد بس": 10, "خد وهات": 10, "see swap": 10, "بصرة": 10,
    "كعب داير": 15, "سكرو أحمر": 25, "الحرامي": 10, "+20": 20
}

def parse_card_value(card_str: str) -> int:
    key = card_key(card_str)
    if key in CARD_POINT_VALUES:
        return CARD_POINT_VALUES[key]
    m = re.search(r'([+-]?\d+)', key)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return 10

def determine_winners(lobby: Lobby):
    hands = lobby.hands
    if not hands:
        return [], {}
    
    # حساب النقاط لكل لاعب
    sums = {p: sum(parse_card_value(c) for c in cards) for p, cards in hands.items()}
    
    # العثور على أقل مجموع نقاط
    min_score = min(sums.values())
    candidates = [p for p, score in sums.items() if score == min_score]
    
    # إذا كان هناك لاعب واحد فقط بأقل نقاط
    if len(candidates) == 1:
        return candidates, {"sums": sums, "counts": {p: len(cards) for p, cards in hands.items()}}
    
    # إذا تعادل عدة لاعبين في النقاط، ننظر إلى عدد الأوراق
    counts = {p: len(hands[p]) for p in candidates}
    min_count = min(counts.values())
    final_candidates = [p for p in candidates if counts[p] == min_count]
    
    return final_candidates, {"sums": sums, "counts": {p: len(cards) for p, cards in hands.items()}}

async def show_end_game_summary(lobby: Lobby, channel: discord.TextChannel):
    # إرسال ملخص النتائج للويب هوك
    try:
        winners, stats = determine_winners(lobby)
        losers = [p for p, s in lobby.scores.items() if s == max(lobby.scores.values())]
        msg = f"🏁 نهاية جولة في {channel.guild.name if getattr(channel, 'guild', None) else 'سيرفر'}\n"
        msg += "الفائزون: " + ", ".join(p.display_name for p in winners) + "\n"
        msg += "الخاسرون: " + ", ".join(p.display_name for p in losers) + "\n"
        msg += "النتائج:\n" + "\n".join(f"{p.display_name}: {lobby.scores.get(p, 0)}" for p in lobby.players)
        await send_webhook_message(msg)
    except Exception as e:
        logger.error(f"Webhook summary failed: {e}")
    if lobby.scrap_player:
        for p in lobby.players:
            lobby.scores.setdefault(p, 0)

        class ThiefSelect(discord.ui.Select):
            def __init__(self, actor, lobby):
                options = [discord.SelectOption(label=p.display_name, value=str(p.id))
                           for p in lobby.players if p != actor]
                super().__init__(placeholder="🔍 اختر لاعب لتقول إنه معه الحرامي",
                                 min_values=1, max_values=1, options=options)
                self.actor = actor
                self.lobby = lobby

            async def callback(self, interaction: discord.Interaction):
                if interaction.user != self.actor:
                    return await interaction.response.send_message("❌ ليس من حقك الاختيار!", ephemeral=True)
                target_id = int(self.values[0])
                target = next((p for p in self.lobby.players if p.id == target_id), None)
                thief_owner = None
                for pl, hand in self.lobby.hands.items():
                    if any(card_key(c) == "الحرامي" for c in hand):
                        thief_owner = pl
                        break
                thief_value = CARD_POINT_VALUES.get("الحرامي", 10)
                if thief_owner and thief_owner == target:
                    self.lobby.scores.setdefault(thief_owner, 0)
                    self.lobby.scores[thief_owner] += thief_value
                    success_embed = discord.Embed(
                        title="🎯 توقع صحيح!",
                        description=f"**{thief_owner.display_name}** كان معه كرت الحرامي 🦹",
                        color=0x2ecc71
                    )
                    success_embed.add_field(name="🎁 النقاط المضافة", value=f"+{thief_value} نقطة", inline=True)
                    await interaction.response.send_message(embed=success_embed, ephemeral=True)
                else:
                    if thief_owner:
                        scr = self.lobby.scrap_player
                        self.lobby.scores.setdefault(scr, 0)
                        self.lobby.scores.setdefault(thief_owner, 0)
                        transfer = thief_value
                        self.lobby.scores[scr] -= transfer
                        self.lobby.scores[thief_owner] += transfer
                        error_embed = discord.Embed(
                            title="❌ توقع خاطئ!",
                            description=f"كرت الحرامي كان مع **{thief_owner.display_name}**",
                            color=0xe74c3c
                        )
                        error_embed.add_field(name="🔄 نقل النقاط", 
                                            value=f"**{transfer}** نقطة انتقلت من {scr.display_name} إلى {thief_owner.display_name}", 
                                            inline=False)
                        await interaction.response.send_message(embed=error_embed, ephemeral=True)
                    else:
                        info_embed = discord.Embed(
                            title="ℹ️ لا يوجد حرامي",
                            description="لم يكن مع أي لاعب كرت الحرامي",
                            color=0x3498db
                        )
                        await interaction.response.send_message(embed=info_embed, ephemeral=True)
                if self.view:
                    self.view.stop()

        class ThiefGuessView(discord.ui.View):
            def __init__(self, actor, lobby, timeout=60):
                super().__init__(timeout=timeout)
                self.actor = actor
                self.lobby = lobby
                self.add_item(ThiefSelect(actor, lobby))

        try:
            thief_embed = discord.Embed(
                title="🦹 تحقيق الحرامي",
                description=f"{lobby.scrap_player.mention} يبدو أنك لاحظت شيئاً مريباً!\n\nاختر اللاعب الذي تعتقد أنه يحمل كرت الحرامي...",
                color=0xf39c12
            )
            thief_embed.set_footer(text="لديك 60 ثانية لاتخاذ القرار")
            thief_view = ThiefGuessView(lobby.scrap_player, lobby)
            await channel.send(embed=thief_embed, view=thief_view)
            await thief_view.wait()
        except Exception:
            error_embed = discord.Embed(
                title="⚠️ خطأ في التحقيق",
                description="فشل تفعيل استعلام الحرامي - المتابعة بدون تأثير الحرامي",
                color=0xe74c3c
            )
            await channel.send(embed=error_embed)

    for p in lobby.players:
        hand = lobby.hands.get(p, [])
        lobby.scores[p] = sum(parse_card_value(c) for c in hand)

    summary_embed = discord.Embed(
        title="🎊 نهاية اللعبة - الملخص النهائي",
        description="**إليك النتائج النهائية للجميع:**",
        color=0xf1c40f
    )
    
    for p in lobby.players:
        hand = lobby.hands.get(p, [])
        score = lobby.scores.get(p, 0)
        cards_count = len(hand)
        icon = "🎯" if cards_count == 0 else "⚠️" if cards_count == 1 else "🃏"
        cards_display = ", ".join(hand) if hand else "**لا يوجد أوراق** 🎉"
        if len(cards_display) > 1024:
            cards_display = cards_display[:1000] + "…"
        summary_embed.add_field(
            name=f"{icon} {p.display_name}",
            value=f"**الأوراق:** {cards_count} | **النقاط:** {score}\n{cards_display}",
            inline=False
        )
    summary_embed.set_footer(text=f"الجولة: {lobby.round_number} | عدد اللاعبين: {len(lobby.players)}")
    await channel.send(embed=summary_embed)

    def format_progress_bar(score, max_score=50, length=15):
        if max_score == 0: max_score = 1
        filled_length = int(length * min(score, max_score) / max_score)
        return "█" * filled_length + "░" * (length - filled_length)

    def medal_for_position(pos):
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        return medals.get(pos, "🎯")

    sorted_players = sorted(lobby.players, key=lambda p: lobby.scores.get(p, 0))
    max_score = max(lobby.scores.values()) if lobby.scores else 10

    leaderboard_embed = discord.Embed(
        title="🏆 جدول المتصدرين",
        description="**الأقل نقاطاً يفوز!** 📊",
        color=0x3498db
    )
    for idx, p in enumerate(sorted_players, start=1):
        score = lobby.scores.get(p, 0)
        medal = medal_for_position(idx)
        bar = format_progress_bar(score, max_score)
        color_icon = "💎" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "🔹"
        leaderboard_embed.add_field(
            name=f"{medal} {color_icon} {p.display_name}",
            value=f"**{score} نقطة**\n`{bar}`",
            inline=False
        )
    leaderboard_embed.set_footer(text="مبروك للفائزين! 🎉")
    await channel.send(embed=leaderboard_embed)

    winners, stats = determine_winners(lobby)
    sums = stats["sums"]
    counts = stats["counts"]

    if not winners:
        no_winner_embed = discord.Embed(
            title="❓ لا يوجد فائز واضح",
            description="لم يتم تحديد فائز في هذه الجولة",
            color=0x95a5a6
        )
        await channel.send(embed=no_winner_embed)
    else:
        if len(winners) == 1:
            winner = winners[0]
            winner_score = sums[winner]
            winner_cards = counts[winner]
            
            winner_embed = discord.Embed(
                title="🎉 مبروك الفوز!",
                description=f"**{winner.mention}** هو الفائز في هذه الجولة! 🏆",
                color=0xf1c40f
            )
            winner_embed.add_field(
                name="📊 إحصائيات الفوز",
                value=f"• **النقاط:** {winner_score}\n• **عدد الأوراق:** {winner_cards}",
                inline=True
            )
            winner_embed.add_field(
                name="🎊 تهانينا!",
                value="لقد أظهرت مهارة رائعة في اللعب!",
                inline=True
            )
            await channel.send(embed=winner_embed)
        else:
            # التعادل
            draw_embed = discord.Embed(
                title="🤝 تعادل رائع!",
                description="**تعادل متكافئ بين اللاعبين:**",
                color=0x9b59b6
            )
            
            for idx, winner in enumerate(winners, 1):
                score = sums[winner]
                cards_count = counts[winner]
                draw_embed.add_field(
                    name=f"🎯 المتعادل {idx} - {winner.display_name}",
                    value=f"النقاط: {score} | الأوراق: {cards_count}",
                    inline=False
                )
            
            draw_embed.add_field(
                name="🎊 تهانينا للجميع!",
                value="أداء رائع من جميع اللاعبين!",
                inline=False
            )
            await channel.send(embed=draw_embed)

    # تحديث نظام النقاط الدائم بعد عرض الملخص
    try:
        guild_id = channel.guild.id if getattr(channel, "guild", None) else 0
        # تسجيل النتائج ومنح نقاط مكافأة بسيطة: الفائز +5، غير الفائز +1
        for p in lobby.players:
            round_score = int(lobby.scores.get(p, 0))
            is_winner = p in winners
            points_manager.record_game_result(guild_id, p.id, round_score, is_winner)
            points_manager.add_points(guild_id, p.id, 5 if is_winner else 1)

            # إرسال إلى الموقع (مزامنة فورية)
            try:
                await _init_sync_client()
                await _safe_call(
                    sync_client.update_points(
                        guild_id,
                        p.id,
                        points=(5 if is_winner else 1),
                        wins=(1 if is_winner else 0),
                        games=1,
                        score=round_score,
                        mode="inc",
                    ),
                    ctx=f"update_points:round_end:user={p.id}",
                )
            except Exception:
                pass

        # إرسال ملخص جوائز النقاط
        awards_lines = []
        for p in lobby.players:
            is_winner = p in winners
            awards_lines.append(f"• {p.display_name}: {'+5' if is_winner else '+1'} نقطة مكافأة")
        awards_text = "\n".join(awards_lines) if awards_lines else "—"
        awards_embed = discord.Embed(
            title="🎁 مكافآت الجولة",
            description=awards_text,
            color=0x2ecc71
        )
        awards_embed.set_footer(text="يمكنك رؤية نقاطك باستخدام الأمر !نقط")
        await channel.send(embed=awards_embed)
    except Exception:
        # لا نكسر اللعبة إذا فشل حفظ النقاط
        pass

@bot.event
async def on_ready():
    """يُنفَّذ عند بدء البوت وتسجيل الدخول بنجاح"""
    print(f"✅ البوت مُشغَّل: {bot.user.name} (ID: {bot.user.id})")
    print(f"🌐 متصل بـ {len(bot.guilds)} سيرفر")
    
    # فحص ملفات الصور المحلية
    images_dir = Path(__file__).parent
    local_images = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg"))
    if local_images:
        print(f"🖼️  تم العثور على {len(local_images)} ملف صورة محلي")
    else:
        print("⚠️  تحذير: لا توجد ملفات صور محلية!")
        print("   💡 ضع ملفات الصور (.png/.jpg) في مجلد البوت")
        print("   📝 أو حدّث روابط CDN في CARD_IMAGES dictionary")
    
        # ملاحظة للأونر
        print("\n" + "="*50)
        print("ℹ️  ملاحظة هامة - أوامر الأونر:")
        print("   📌 الأوامر الخاصة (reward, vip, control, etc.)")
        print("   📌 تظهر فقط للأعضاء ذوي صلاحيات Administrator")
        print("   📌 لكن هناك فحص مزدوج داخل كل أمر للتأكد")
        print("   ✅ فقط الأونر الحقيقي يمكنه استخدامها")
        print("="*50 + "\n")
    
    # مزامنة slash commands تلقائياً
    try:
        print("⏳ جاري مزامنة slash commands...")
        synced = await bot.tree.sync()
        print(f"✅ تمت مزامنة {len(synced)} أمر slash بنجاح!")
        
        # عرض قائمة الأوامر المُسجَّلة
        commands_list = [cmd.name for cmd in synced]
        print(f"📋 الأوامر المُسجَّلة: {', '.join(commands_list[:10])}")
        if len(commands_list) > 10:
            print(f"   ... و {len(commands_list) - 10} أمر آخر")
        
    except Exception as e:
        print(f"❌ فشلت مزامنة slash commands: {e}")
    
    # تعيين حالة البوت
    try:
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name="سكرووو | /help للمساعدة"
            )
        )
        print("✅ تم تعيين حالة البوت")
    except Exception as e:
        print(f"⚠️ فشل تعيين الحالة: {e}")
    
    print("=" * 50)
    print("🎴 البوت جاهز للاستخدام!")
    print("=" * 50)

@bot.event
async def on_close():
    # For completeness; discord.py uses bot.close/logout
    try:
        if aiohttp_session and not aiohttp_session.closed:
            await aiohttp_session.close()
    except Exception:
        pass

@bot.event
async def on_member_remove(member: discord.Member):
    """يُنفَّذ عندما يخرج عضو من السيرفر - إزالته من الألعاب النشطة"""
    try:
        # البحث عن اللاعب في أي لوبي نشط
        for channel_id, lobby in list(active_lobbies.items()):
            if member in lobby.players:
                # إزالة اللاعب من اللعبة
                lobby.players.remove(member)
                
                # إزالة أوراقه
                if member in lobby.hands:
                    lobby.hands.pop(member)
                
                # إرسال إشعار
                try:
                    channel = bot.get_channel(channel_id)
                    if channel:
                        leave_embed = discord.Embed(
                            title="👋 لاعب غادر السيرفر",
                            description=f"**{member.display_name}** غادر السيرفر وتم إزالته من اللعبة",
                            color=0x95a5a6
                        )
                        leave_embed.add_field(
                            name="👥 اللاعبين المتبقين",
                            value=f"{len(lobby.players)} لاعب",
                            inline=True
                        )
                        await channel.send(embed=leave_embed)
                        
                        # فحص إذا بقى لاعب واحد فقط - إقفال اللعبة
                        if len(lobby.players) <= 1:
                            end_embed = discord.Embed(
                                title="🛑 إنهاء اللعبة تلقائياً",
                                description="**تم إنهاء اللعبة لعدم وجود لاعبين كافيين!**",
                                color=0xe74c3c
                            )
                            if lobby.players:
                                end_embed.add_field(
                                    name="🏆 الفائز",
                                    value=f"**{lobby.players[0].display_name}** فاز بشكل افتراضي!",
                                    inline=False
                                )
                            await channel.send(embed=end_embed)
                            
                            # تنظيف اللوبي وإزالته
                            lobby.cleanup_lobby()
                            active_lobbies.pop(channel_id, None)
                except Exception as e:
                    logger.error(f"Error handling member leave in lobby: {e}")
    except Exception as e:
        logger.error(f"Error in on_member_remove: {e}")

# -----------------------------
# واجهات اللاعبين
# -----------------------------
class PlayerSelectionView(View):
    def __init__(self, lobby: Lobby):
        super().__init__(timeout=20)
        self.lobby = lobby
        for player in lobby.players:
            self.add_item(PlayerSelectButton(player, lobby))

class PlayerSelectButton(Button):
    def __init__(self, player, lobby: Lobby):
        colors = [discord.ButtonStyle.primary, discord.ButtonStyle.success, 
                 discord.ButtonStyle.danger, discord.ButtonStyle.secondary]
        color = colors[len(lobby.players) % len(colors)]
        super().__init__(label=f"👤 {player.display_name}", style=color)
        self.player = player
        self.lobby = lobby

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            error_embed = discord.Embed(title="❌ غير مسموح", description="هذا الزر مخصص لك فقط!", color=0xe74c3c)
            return await interaction.response.send_message(embed=error_embed, ephemeral=True)
        if self.player in self.lobby.players_viewed_cards:
            warning_embed = discord.Embed(title="⚠️ سبق المشاهدة", description="لقد شاهدت أوراقك بالفعل!", color=0xf39c12)
            return await interaction.response.send_message(embed=warning_embed, ephemeral=True)
        hand = self.lobby.hands.get(self.player, [])
        if not hand:
            error_embed = discord.Embed(title="❌ لا توجد أوراق", description="لا يوجد أوراق في يدك!", color=0xe74c3c)
            return await interaction.response.send_message(embed=error_embed, ephemeral=True)
        view = CardView(self.player, hand, self.lobby)
        # مزايا حسب الرتبة
        if is_owner(self.player):
            max_cards = 4
            status_icon = " 👑"
            status_desc = "**مزايا الملك: يمكنك مشاهدة 4 أوراق! تحكم كامل!** 🔥"
            embed_color = 0xFFD700
        elif is_vip(self.player):
            max_cards = 3
            vip_tier = get_vip_tier(self.player)
            if "Diamond" in vip_tier:
                status_icon = " �"
            elif "Gold" in vip_tier:
                status_icon = " 🌟"
            elif "Silver" in vip_tier:
                status_icon = " ⭐"
            else:
                status_icon = " 🎖️"
            status_desc = f"**مزايا {vip_tier}: يمكنك مشاهدة 3 أوراق بدلاً من 2!** ✨"
            embed_color = get_vip_embed_color(self.player)
        else:
            max_cards = 2
            status_icon = ""
            status_desc = "**يمكنك مشاهدة ورقتين فقط من أصل 4 أوراق!**"
            embed_color = 0x9b59b6
        
        hand_embed = discord.Embed(
            title=f"🃏 أوراقك الخاصة{status_icon}",
            description=f"{status_desc}\n\nاضغط على الأزرار أدناه لمشاهدة محتوى كل ورقة...",
            color=embed_color
        )
        hand_embed.add_field(name="💡 تلميح", value="قيم الأوراق مخفية - اختر بحكمة عشان متتفشخش!", inline=False)
        
        # إضافة مزايا خاصة حسب الرتبة
        if is_owner(self.player):
            hand_embed.add_field(name="👑 مزايا الملك", value="• مشاهدة 4 أوراق\n• أوامر حصرية\n• ألوان ذهبية", inline=True)
        elif is_vip(self.player):
            vip_tier = get_vip_tier(self.player)
            hand_embed.add_field(name=f"🎖️ مزايا {vip_tier}", value="• مشاهدة 3 أوراق\n• ألوان مميزة\n• أولوية خاصة", inline=True)
        
        footer_text = f"لديك 30 ثانية لمشاهدة {max_cards} أوراق"
        hand_embed.set_footer(text=footer_text)
        await interaction.response.send_message(embed=hand_embed, view=view, ephemeral=True)

class CardView(View):
    def __init__(self, player, hand, lobby: Lobby):
        super().__init__(timeout=30)
        self.player = player
        self.hand = hand
        self.lobby = lobby
        self.cards_viewed = 0
        # مزايا حسب الرتبة: أونر 4 أوراق، VIP 3 أوراق، عادي 2 أوراق
        if is_owner(player):
            self.max_views = 4
        elif is_vip(player):
            self.max_views = 3
        else:
            self.max_views = 2
        for idx in range(len(hand)):
            colors = [discord.ButtonStyle.primary, discord.ButtonStyle.success, 
                     discord.ButtonStyle.danger, discord.ButtonStyle.secondary]
            color = colors[idx % len(colors)]
            self.add_item(CardButton(idx, player, hand, self, color))

class CardButton(Button):
    def __init__(self, idx, player, hand, parent_view, button_style):
        super().__init__(label=f"🎴 ورقة {idx+1}", style=button_style)
        self.idx = idx
        self.player = player
        self.hand = hand
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            error_embed = discord.Embed(title="❌ غير مسموح", description="هذا الزر مخصص لك فقط!", color=0xe74c3c)
            return await interaction.response.send_message(embed=error_embed, ephemeral=True)
        if self.parent_view.cards_viewed >= self.parent_view.max_views:
            warning_embed = discord.Embed(title="⚠️ حد المشاهدة", description="لقد استنفذت عدد المرات المسموح بها!", color=0xf39c12)
            return await interaction.response.send_message(embed=warning_embed, ephemeral=True)
        if self.idx >= len(self.hand):
            error_embed = discord.Embed(title="❌ خطأ", description="هذه الورقة غير متاحة!", color=0xe74c3c)
            return await interaction.response.send_message(embed=error_embed, ephemeral=True)
        card = self.hand[self.idx]
        self.parent_view.cards_viewed += 1
        await send_card(None, card, title=f"🎴 الورقة رقم {self.idx+1}", interaction=interaction, ephemeral=True)
        if self.parent_view.cards_viewed >= self.parent_view.max_views:
            self.parent_view.lobby.players_viewed_cards.add(self.player)
            remaining_players = len(self.parent_view.lobby.players) - len(self.parent_view.lobby.players_viewed_cards)
            completion_embed = discord.Embed(
                title="✅ اكتمل المشاهدة",
                description="**تم الانتهاء من مشاهدة أوراقك!** 🎉",
                color=0x2ecc71
            )
            completion_embed.add_field(
                name="📊 الحالة",
                value=f"يمكنك مشاهدة ورقتين فقط وقد انتهيت منهم\n⏳ بانتظار **{remaining_players}** لاعب لإكمال مشاهدة أوراقهم...",
                inline=False
            )
            for child in self.parent_view.children:
                child.disabled = True
            try:
                await interaction.message.edit(embed=completion_embed, view=self.parent_view)
            except Exception:
                # الرسالة قد تكون اتمسحت/أصبحت Unknown Message أثناء التفاعل
                pass

# -----------------------------
# واجهات الانضمام
# -----------------------------
class JoinButton(Button):
    def __init__(self, lobby: Lobby, message_holder):
        super().__init__(label="🎮 انضم للعبة", style=discord.ButtonStyle.success)
        self.lobby = lobby
        self.message_holder = message_holder

    async def callback(self, interaction: discord.Interaction):
        # VIP-only restriction
        if getattr(self.lobby, 'vip_mode', False) and not is_vip(interaction.user):
            return await interaction.response.send_message("❌ هذه الغرفة للـ VIP فقط!", ephemeral=True)
        if interaction.user in self.lobby.players:
            warning_embed = discord.Embed(title="⚠️ سبق الانضمام", description="أنت منضم بالفعل للعبة!", color=0xf39c12)
            return await interaction.response.send_message(embed=warning_embed, ephemeral=True)
        if len(self.lobby.players) >= 8:
            error_embed = discord.Embed(title="❌ الغرفة ممتلئة", description="اللعبة وصلت للحد الأقصى (8 لاعبين)", color=0xe74c3c)
            return await interaction.response.send_message(embed=error_embed, ephemeral=True)
        self.lobby.players.append(interaction.user)
        success_embed = discord.Embed(title="✅ انضممت بنجاح!", description=f"**{interaction.user.display_name}** انضم للعبة 🎉", color=0x2ecc71)
        await interaction.response.send_message(embed=success_embed, ephemeral=True)
        await interaction.message.edit(embed=generate_lobby_embed(self.lobby, 0), view=self.view)
        if len(self.lobby.players) >= 8:
            for child in self.view.children:
                if isinstance(child, JoinButton):
                    child.disabled = True
            full_embed = discord.Embed(title="🎊 اكتمل العدد!", description="**اكتمل عدد اللاعبين (8/8)**\n\nاللعبة ستبدأ قريباً...", color=0x9b59b6)
            await interaction.message.edit(embed=full_embed, view=self.view)

class LeaveButton(Button):
    def __init__(self, lobby: Lobby, message_holder):
        super().__init__(label="🚫 غادر الغرفة", style=discord.ButtonStyle.danger)
        self.lobby = lobby
        self.message_holder = message_holder

    async def callback(self, interaction: discord.Interaction):
        if interaction.user not in self.lobby.players:
            error_embed = discord.Embed(title="❌ لست منضماً", description="أنت لست منضماً للعبة أصلاً!", color=0xe74c3c)
            return await interaction.response.send_message(embed=error_embed, ephemeral=True)
        self.lobby.players.remove(interaction.user)
        leave_embed = discord.Embed(title="👋 غادرت اللعبة", description=f"**{interaction.user.display_name}** غادر الغرفة", color=0x95a5a6)
        await interaction.response.send_message(embed=leave_embed, ephemeral=True)
        await interaction.message.edit(embed=generate_lobby_embed(self.lobby, 0), view=self.view)

class JoinView(View):
    def __init__(self, lobby: Lobby, msg_holder):
        super().__init__(timeout=None)
        self.lobby = lobby
        self.msg_holder = msg_holder
        self.add_item(JoinButton(lobby, msg_holder))
        self.add_item(LeaveButton(lobby, msg_holder))

# -----------------------------
# واجهات اللعب الرئيسية
# -----------------------------
class DrawCardView(View):
    def __init__(self, player, deck, hand, lobby: Lobby):
        super().__init__(timeout=30)
        self.player = player
        self.deck = deck
        self.hand = hand
        self.lobby = lobby
        self.add_item(DrawCardButton(player, deck, hand, lobby, parent_view=self))
        # السكرو متاح من الجولة الخامسة ولو محدش عمل سكرو قبل كده
        if self.lobby.round_number >= 5 and not self.lobby.scrap_player:
            self.add_item(ScrapButton(player, self.lobby, parent_view=self))
        # خد من الأرض متاح لو فيه أوراق على الأرض
        if self.lobby.ground:
            self.add_item(GroundTakeButton(player, self.lobby, parent_view=self))
        # التبصير متاح دايماً
        self.add_item(TebsarButton(player, self.lobby, parent_view=self))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            if hasattr(self, 'message') and self.message:
                timeout_embed = discord.Embed(
                    title="⏰ انتهى الوقت", 
                    description="انتهى وقت الاختيار", 
                    color=0x95a5a6
                )
                await self.message.edit(embed=timeout_embed, view=self)
        except Exception:
            pass
        
        # إيقاف الـ view
        self.stop()

class DrawCardButton(Button):
    def __init__(self, player, deck, hand, lobby: Lobby, parent_view: View):
        super().__init__(label="🎴 اسحب ورقة", style=discord.ButtonStyle.success)
        self.player = player
        self.deck = deck
        self.hand = hand
        self.lobby = lobby
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if self.lobby.current_draw_active:
            return await interaction.response.send_message("⏳ انتظر حتى تنتهي من التفاعل الحالي!", ephemeral=True)
        if interaction.user != self.player:
            error_embed = discord.Embed(title="❌ ليس دورك", description="هذا الزر ليس مخصصاً لك!", color=0xe74c3c)
            return await interaction.response.send_message(embed=error_embed, ephemeral=True)
        if self.lobby.current_turn_player != self.player:
            error_embed = discord.Embed(title="❌ ليس دورك حالياً", description="الرجاء الانتظار لدورك!", color=0xe74c3c)
            return await interaction.response.send_message(embed=error_embed, ephemeral=True)
        if not self.deck:
            refilled = refill_deck_from_ground(self.lobby)
            if refilled:
                info_embed = discord.Embed(title="🔄 إعادة تعبئة", description="تم إعادة تعبئة الديك من أوراق الأرض", color=0x3498db)
                return await interaction.response.send_message(embed=info_embed, ephemeral=True)
            else:
                error_embed = discord.Embed(title="❌ لا توجد أوراق", description="لا توجد أوراق متاحة للسحب!", color=0xe74c3c)
                return await interaction.response.send_message(embed=error_embed, ephemeral=True)
        
        # إيقاف الـ view الحالي وتعطيل أزراره
        try:
            for child in self.parent_view.children:
                child.disabled = True
            if getattr(self.parent_view, "message", None):
                await self.parent_view.message.edit(view=self.parent_view)
        except Exception:
            pass
        
        self.lobby.current_draw_active = True
        try:
            card = self.deck.pop()
            view = KeepOrThrowView(self.player, card, self.hand, self.deck, interaction, self.lobby, parent_draw_view=self.parent_view)
            await send_card(None, card, title="🎴 ورقة جديدة", interaction=interaction, ephemeral=True)
            choice_embed = discord.Embed(title="🤔 خيارات الورقة", description="**ماذا تريد أن تفعل بهذه الورقة?**", color=0xf39c12)
            choice_embed.set_footer(text="لديك 30 ثانية لاتخاذ القرار")
            await interaction.followup.send(embed=choice_embed, view=view, ephemeral=True)
        finally:
            self.lobby.current_draw_active = False

class KeepOrThrowView(View):
    def __init__(self, player, new_card, player_hand, deck, interaction, lobby: Lobby, parent_draw_view: View):
        super().__init__(timeout=30)
        self.player = player
        self.new_card = new_card
        self.player_hand = player_hand
        self.deck = deck
        self.interaction = interaction
        self.lobby = lobby
        self.parent_draw_view = parent_draw_view
        card_str = str(new_card).strip()
        # بينج: زر واحد ارمي فقط
        if card_str == "بينج":
            self.add_item(PingThrowButton(player, new_card, deck, interaction.channel, player_hand, lobby, parent_draw_view))
        # بونج: زر واحد بدل فقط
        elif card_str == "بونج":
            self.add_item(PongSwapButton(player, new_card, player_hand, deck, interaction.channel, lobby, parent_draw_view))
        else:
            self.add_item(ThrowButton(player, new_card, deck, interaction.channel, player_hand, lobby, parent_draw_view))
            self.add_item(KeepButton(player, new_card, player_hand, deck, interaction.channel, lobby, parent_draw_view))

# زر خاص بينج: يرمي الورقة ويعمل سكيب
class PingThrowButton(Button):
    def __init__(self, player, card, deck, channel, player_hand, lobby: Lobby, parent_draw_view: View):
        super().__init__(label="🗑 ارمي بينج (سكيب)", style=discord.ButtonStyle.danger)
        self.player = player
        self.card = card
        self.deck = deck
        self.channel = channel
        self.player_hand = player_hand
        self.lobby = lobby
        self.parent_draw_view = parent_draw_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش دورك!", ephemeral=True)
        if self.lobby.current_turn_player != self.player:
            return await interaction.response.send_message("❌ مش دورك دلوقتي!", ephemeral=True)
        if self.view:
            self.view.stop()
        self.lobby.ground.append(self.card)
        await send_card(interaction.channel, self.card, title=f"🎴 {self.player.display_name} رمى بينج (سكيب)")
        await interaction.response.send_message("✅ تم رمي بينج. تم سكيب اللاعب اللي بعدك!", ephemeral=True)
        # ضع علامة سكيب للدور القادم
        self.lobby._skip_next_turn = True
        # إنهاء الدور
        try:
            for child in self.parent_draw_view.children:
                child.disabled = True
            if getattr(self.parent_draw_view, "message", None):
                await self.parent_draw_view.message.edit(view=self.parent_draw_view)
        except Exception:
            pass
        self.parent_draw_view.stop()
        self.lobby.hands[self.player] = self.player_hand

# زر خاص بونج: بدل فقط ولو في بينج على الأرض يعمل سكيب بعد التبديل
class PongSwapButton(Button):
    def __init__(self, player, card, player_hand, deck, channel, lobby: Lobby, parent_draw_view: View):
        super().__init__(label="🔄 بدل بورقة من معاك", style=discord.ButtonStyle.primary)
        self.player = player
        self.card = card
        self.player_hand = player_hand
        self.deck = deck
        self.channel = channel
        self.lobby = lobby
        self.parent_draw_view = parent_draw_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش دورك!", ephemeral=True)
        if self.lobby.current_turn_player != self.player:
            return await interaction.response.send_message("❌ مش دورك دلوقتي!", ephemeral=True)
        if self.view:
            self.view.stop()
        # عرض اختيار ورقة من اليد
        view = SwapKeepView(self.player, self.card, self.player_hand, self.deck, self.lobby, parent_draw_view=self.parent_draw_view)
        await interaction.response.send_message("🔄 اختر ورقة من يدك لتبديلها مع بونج:", view=view, ephemeral=True)
        # بعد التبديل، لو في بينج على الأرض، سكيب الدور القادم
        if any(str(card).strip() == "بينج" for card in self.lobby.ground):
            self.lobby._skip_next_turn = True
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class ThrowButton(Button):
    def __init__(self, player, card, deck, channel, player_hand, lobby: Lobby, parent_draw_view: View):
        super().__init__(label="🗑 ارمي الورقة", style=discord.ButtonStyle.danger)
        self.player = player
        self.card = card
        self.deck = deck
        self.channel = channel
        self.player_hand = player_hand
        self.lobby = lobby
        self.parent_draw_view = parent_draw_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش دورك!", ephemeral=True)
        if self.lobby.current_turn_player != self.player:
            return await interaction.response.send_message("❌ مش دورك دلوقتي!", ephemeral=True)
        
        # إيقاف الـ view بتاع الاختيار فوراً
        if self.view:
            self.view.stop()
        
        self.lobby.ground.append(self.card)
        await send_card(interaction.channel, self.card, title=f"🎴 {self.player.display_name} رمى ورقة")
        
        # إرسال رد للمستخدم
        await interaction.response.send_message("✅ تم رمي الورقة", ephemeral=True)
        
        # معالجة البطاقة الخاصة
        handler = SpecialCardHandler(self.player, self.card, self.player_hand, interaction, self.channel, self.lobby)
        await handler.handle()
        
        # إذا كانت البطاقة تحتاج انتظار، ننتظر قبل إنهاء الدور
        if handler.needs_wait and self.lobby.pending_interactions:
            # إضافة رسالة تنبيه
            await self.channel.send(
                f"⏳ **انتظر {self.player.display_name}** - يجب إنهاء التفاعل مع البطاقة أولاً..."
            )
            
            # انتظار انتهاء كل التفاعلات النشطة
            max_wait = 20  # أقصى وقت انتظار
            waited = 0
            while self.lobby.pending_interactions and waited < max_wait:
                await asyncio.sleep(1)
                waited += 1
            
            if waited >= max_wait:
                await self.channel.send(f"⚠️ انتهى وقت الانتظار لـ {self.player.display_name}، سيتم الانتقال للدور التالي")
                # مسح التفاعلات المعلقة
                self.lobby.pending_interactions.clear()
        
        try:
            # إنهاء دور اللاعب بعد التأكد من انتهاء التفاعل
            for child in self.parent_draw_view.children:
                child.disabled = True
            if getattr(self.parent_draw_view, "message", None):
                await self.parent_draw_view.message.edit(view=self.parent_draw_view)
        except Exception:
            pass
        self.parent_draw_view.stop()
        self.lobby.hands[self.player] = self.player_hand

class KeepButton(Button):
    def __init__(self, player, card, player_hand, deck, channel, lobby: Lobby, parent_draw_view: View):
        super().__init__(label="💾 احتفظ بالورقة", style=discord.ButtonStyle.success)
        self.player = player
        self.card = card
        self.player_hand = player_hand
        self.deck = deck
        self.channel = channel
        self.lobby = lobby
        self.parent_draw_view = parent_draw_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش دورك!", ephemeral=True)
        if self.lobby.current_turn_player != self.player:
            return await interaction.response.send_message("❌ مش دورك دلوقتي!", ephemeral=True)
        
        # إيقاف الـ view الحالي
        if self.view:
            self.view.stop()
        
        view = SwapKeepView(self.player, self.card, self.player_hand, self.deck, self.lobby, parent_draw_view=self.parent_draw_view)
        await interaction.response.send_message("🔄 اختار أي ورقة من إيدك تتبدل بالورقة الجديدة:", view=view, ephemeral=True)

class SwapKeepView(View):
    def __init__(self, player, new_card, hand, deck, lobby: Lobby, timeout=30, parent_draw_view: View=None):
        super().__init__(timeout=timeout)
        self.player = player
        self.new_card = new_card
        self.hand = hand
        self.deck = deck
        self.lobby = lobby
        self.parent_draw_view = parent_draw_view
        for idx, _ in enumerate(list(hand)):
            self.add_item(KeepSwapButton(idx, player, new_card, hand, deck, lobby, parent_draw_view))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class KeepSwapButton(Button):
    def __init__(self, idx, player, new_card, hand, deck, lobby: Lobby, parent_draw_view: View):
        super().__init__(label=f"🎴 ورقة {idx+1}", style=discord.ButtonStyle.primary)
        self.idx = idx
        self.player = player
        self.new_card = new_card
        self.hand = hand
        self.deck = deck
        self.lobby = lobby
        self.parent_draw_view = parent_draw_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        if self.lobby.current_turn_player != self.player:
            return await interaction.response.send_message("❌ مش دورك دلوقتي!", ephemeral=True)
        if self.idx >= len(self.hand):
            return await interaction.response.send_message("❌ الورقة مش متاحة!", ephemeral=True)
        old = self.hand[self.idx]
        self.hand[self.idx] = self.new_card
        self.lobby.ground.append(old)
        self.lobby.hands[self.player] = self.hand
        await interaction.response.send_message("✅ استبدلت ورقة (تم الادخال في يدك).", ephemeral=True)
        await send_card(self.lobby.channel, old, title=f"🔄 {self.player.display_name} الورقة التي اترمت على الأرض")
        if self.view:
            self.view.stop()
        try:
            for child in self.parent_draw_view.children:
                child.disabled = True
            if getattr(self.parent_draw_view, "message", None):
                await self.parent_draw_view.message.edit(view=self.parent_draw_view)
        except Exception:
            pass
        self.parent_draw_view.stop()

# -----------------------------
# الأزرار الخاصة
# -----------------------------
class GroundTakeButton(Button):
    def __init__(self, player, lobby: Lobby, parent_view: View):
        super().__init__(label="📥 خد من الأرض", style=discord.ButtonStyle.success)
        self.player = player
        self.lobby = lobby
        self.parent_draw_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش دورك!", ephemeral=True)
        if self.lobby.current_turn_player != self.player:
            return await interaction.response.send_message("❌ مش دورك دلوقتي!", ephemeral=True)
        if not self.lobby.ground:
            return await interaction.response.send_message("❌ مافيش ورق على الأرض!", ephemeral=True)
        
        # إيقاف الـ view الرئيسي
        try:
            for child in self.parent_draw_view.children:
                child.disabled = True
            if getattr(self.parent_draw_view, "message", None):
                await self.parent_draw_view.message.edit(view=self.parent_draw_view)
        except Exception:
            pass
        
        await self.lobby.channel.send(f"🟢 {interaction.user.display_name} اختار ياخد من الأرض.")
        last_card = self.lobby.ground[-1]
        view = ReplaceWithGroundView(self.player, self.lobby, parent_draw_view=self.parent_draw_view)
        await send_card(None, last_card, title="🎴 الورقة الأخيرة على الأرض", interaction=interaction, ephemeral=True)
        await interaction.followup.send("🔄 اختار ورقة من إيدك عشان تبدلها بها:", view=view, ephemeral=True)

class ReplaceWithGroundView(View):
    def __init__(self, player, lobby: Lobby, timeout=30, parent_draw_view: View=None):
        super().__init__(timeout=timeout)
        self.player = player
        self.lobby = lobby
        self.parent_draw_view = parent_draw_view
        hand = self.lobby.hands.get(self.player, [])
        for idx, _ in enumerate(hand):
            self.add_item(ReplaceGroundChoiceButton(idx, player, lobby, parent_draw_view))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class ReplaceGroundChoiceButton(Button):
    def __init__(self, idx, player, lobby: Lobby, parent_draw_view: View):
        super().__init__(label=f"🎴 ورقة {idx+1}", style=discord.ButtonStyle.primary)
        self.idx = idx
        self.player = player
        self.lobby = lobby
        self.parent_draw_view = parent_draw_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        if self.lobby.current_turn_player != self.player:
            return await interaction.response.send_message("❌ مش دورك دلوقتي!", ephemeral=True)
        hand = self.lobby.hands.get(self.player, [])
        if self.idx >= len(hand):
            return await interaction.response.send_message("❌ الورقة مش متاحة!", ephemeral=True)
        if not self.lobby.ground:
            return await interaction.response.send_message("❌ الورقة مش موجودة على الأرض!", ephemeral=True)
        ground_card = self.lobby.ground.pop()
        old = hand[self.idx]
        hand[self.idx] = ground_card
        self.lobby.ground.append(old)
        self.lobby.hands[self.player] = hand
        await send_card(None, ground_card, title=f"✅ استبدلت ورقة {old} بـ", interaction=interaction, ephemeral=True)
        await send_card(self.lobby.channel, old, title=f"🔄 {self.player.display_name} استبدل واخد من الأرض")
        if self.view:
            self.view.stop()
        try:
            for child in self.parent_draw_view.children:
                child.disabled = True
            if getattr(self.parent_draw_view, "message", None):
                await self.parent_draw_view.message.edit(view=self.parent_draw_view)
        except Exception:
            pass
        self.parent_draw_view.stop()

class TebsarButton(Button):
    def __init__(self, player, lobby: Lobby, parent_view: View):
        super().__init__(label="👁 تبصر", style=discord.ButtonStyle.primary)
        self.player = player
        self.lobby = lobby
        self.parent_draw_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش دورك!", ephemeral=True)
        if self.lobby.current_turn_player != self.player:
            return await interaction.response.send_message("❌ مش دورك دلوقتي!", ephemeral=True)
        
        # إيقاف الـ view الرئيسي
        try:
            for child in self.parent_draw_view.children:
                child.disabled = True
            if getattr(self.parent_draw_view, "message", None):
                await self.parent_draw_view.message.edit(view=self.parent_draw_view)
        except Exception:
            pass
        
        await self.lobby.channel.send(f"👁️ {interaction.user.display_name} اختار يبصر.")
        hand = self.lobby.hands.get(self.player, [])
        if not hand:
            return await interaction.response.send_message("❌ معندكش ورق تتبص عليه!", ephemeral=True)
        view = TebsarChooseView(self.player, self.lobby, parent_draw_view=self.parent_draw_view)
        await interaction.response.send_message("🔍 اختار ورقة عشان تبص عليها:", view=view, ephemeral=True)

class TebsarChooseView(View):
    def __init__(self, player, lobby: Lobby, timeout=30, parent_draw_view: View=None):
        super().__init__(timeout=timeout)
        self.player = player
        self.lobby = lobby
        self.parent_draw_view = parent_draw_view
        hand = list(self.lobby.hands.get(player, []))
        for idx, _ in enumerate(hand):
            self.add_item(TebsarChooseButton(idx, player, lobby, parent_draw_view))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class TebsarChooseButton(Button):
    def __init__(self, idx, player, lobby: Lobby, parent_draw_view: View):
        super().__init__(label=f"🎴 ورقة {idx+1}", style=discord.ButtonStyle.primary)
        self.idx = idx
        self.player = player
        self.lobby = lobby
        self.parent_draw_view = parent_draw_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        if self.lobby.current_turn_player != self.player:
            return await interaction.response.send_message("❌ مش دورك دلوقتي!", ephemeral=True)
        hand = self.lobby.hands.get(self.player, [])
        if not hand or self.idx >= len(hand):
            return await interaction.response.send_message("❌ الورقة مش متاحة!", ephemeral=True)
        if not self.lobby.ground:
            return await interaction.response.send_message("❌ مافيش ورق على الأرض!", ephemeral=True)
        chosen_card = hand[self.idx]
        ground_card = self.lobby.ground[-1]
        if card_key(chosen_card) == card_key(ground_card):
            removed = hand.pop(self.idx)
            self.lobby.hands[self.player] = hand
            await interaction.response.send_message(f"✅ ممتاز! الورقة **{removed}** متطابقة وتم التخلص منها.", ephemeral=True)
            await self.lobby.channel.send(f"✅ {interaction.user.display_name} بصر صح وتخلص من ورقة.")
            try:
                for child in self.parent_draw_view.children:
                    child.disabled = True
                if getattr(self.parent_draw_view, "message", None):
                    await self.parent_draw_view.message.edit(view=self.parent_draw_view)
            except Exception:
                pass
            self.parent_draw_view.stop()
        else:
            taken = self.lobby.ground.pop()
            self.lobby.hands[self.player].append(taken)
            await interaction.response.send_message(f"❌ مش متطابقة. أخدت آخر ورقة من الأرض.", ephemeral=True)
            await self.lobby.channel.send(f"❌ {interaction.user.display_name} بصر ورقة غلط وسحب ورقة زيادة!")
            try:
                for child in self.parent_draw_view.children:
                    child.disabled = True
                if getattr(self.parent_draw_view, "message", None):
                    await self.parent_draw_view.message.edit(view=self.parent_draw_view)
            except Exception:
                pass
            self.parent_draw_view.stop()

class ScrapButton(Button):
    def __init__(self, player, lobby: Lobby, parent_view: View=None):
        super().__init__(label="🚨 سكرو", style=discord.ButtonStyle.danger)
        self.player = player
        self.lobby = lobby
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش دورك!", ephemeral=True)
        
        # تسجيل إعلان السكرو
        self.lobby.scrap_player = self.player
        
        # لون خاص للأونر في إعلان السكرو
        embed_color = get_owner_embed_color(self.player)
        crown_symbol = "👑 " if is_owner(self.player) else ""
        scrap_embed = discord.Embed(
            title=f"🚨 إعلان سكرو! {crown_symbol}",
            description=f"**{format_member(self.player)} أعلن سكرو!**\n\nاللعبة هتنتهي أول ما ييجي دوره تاني.",
            color=embed_color
        )
        await interaction.response.send_message(embed=scrap_embed, ephemeral=False)
        
        # إيقاف الـ view الحالي
        if self.view:
            self.view.stop()
        
        # إيقاف واجهة الدور مباشرة
        try:
            if self.parent_view:
                for child in self.parent_view.children:
                    child.disabled = True
                if getattr(self.parent_view, "message", None):
                    await self.parent_view.message.edit(view=self.parent_view)
                self.parent_view.stop()
        except Exception:
            pass

# -----------------------------
# معالج البطاقات الخاصة
# -----------------------------
class SpecialCardHandler:
    def __init__(self, player, card, player_hand, interaction, channel, lobby: Lobby):
        self.player = player
        self.card = card
        self.player_hand = player_hand
        self.interaction = interaction
        self.channel = channel
        self.lobby = lobby
        self.needs_wait = False  # علامة للبطاقات التي تحتاج انتظار

    async def handle(self):
        card_name = card_key(self.card)
        # --- كروت جديدة لمود التيمات ---
        if card_name == "بينج":
            await send_webhook_message(f"🏓 {self.player.display_name} استخدم كرت بينج!")
            # يجب رميها فوراً، قيمتها 10، عند رميها: اللاعب التالي (من الفريق الخصم) يتم تخطي دوره
            embed = discord.Embed(
                title="🔔 كرت بينج!",
                description=f"**{self.player.display_name}** رمى كرت بينج! سيتم تخطي دور الخصم التالي.\nلو زميلك معاه بونج يقدر يرميها فوراً!",
                color=0xffc300
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1423980446382948373/1427996309960396841/Untitled_design.png?ex=68f0e4b3&is=68ef9333&hm=9770c3edb7f21554649e5941ba42e57381167a3d46310ab9b2d11a7d864f9712&")
            await self.channel.send(embed=embed)
            # منطق السكيب والبونج سيتم ربطه في حلقة الأدوار (يحتاج تعديل في start_round)
        elif card_name == "بونج":
            await send_webhook_message(f"🥁 {self.player.display_name} استخدم كرت بونج!")
            # يجب الاحتفاظ بها عند السحب، لكن يمكن رميها كتِبصيرة بعد بينج
            embed = discord.Embed(
                title="🥁 كرت بونج!",
                description=f"**{self.player.display_name}** معاه كرت بونج!\nيمكنك رميها فقط بعد بينج من زميلك كتِبصيرة.",
                color=0x00e6fe
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1423980446382948373/1427996309209743472/Untitled_design_2.png?ex=68f0e4b3&is=68ef9333&hm=3f1dedb244d82d384d79a1f64db9fcb0d621045be6a39a5678b430ac109fba15&")
            await self.channel.send(embed=embed)
            # منطق رميها كتِبصيرة سيتم ربطه في حلقة الأدوار
        elif card_name == "على كيفك":
            await send_webhook_message(f"🎲 {self.player.display_name} استخدم كرت على كيفك!")
            # عند رميها من الأرض، يظهر اختيار نوع الكرت
            embed = discord.Embed(
                title="🎲 كرت على كيفك!",
                description=f"**{self.player.display_name}** استخدم كرت على كيفك! اختر نوع الكرت الذي تريد نسخه.",
                color=0x8e44ad
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1423980446382948373/1427996309557612607/Untitled_design_1.png?ex=68f0e4b3&is=68ef9333&hm=099295ea2489178edd16e6f8758b0da9f60b828d5a4211ad0fadbd3b35852aa3&")
            await self.channel.send(embed=embed)
            # منطق اختيار الكرت سيتم ربطه بواجهة تفاعلية لاحقاً
        # --- باقي الكروت ---
        elif card_name in ["9", "10"]:
            self.needs_wait = True
            await self._handle_look_other(wait_for_view=True)
        elif card_name in ["7", "8"]:
            self.needs_wait = True
            await self._handle_look_self(wait_for_view=True)
        elif card_name == "خد بس":
            self.needs_wait = True  # تحتاج انتظار الإهداء
            await self._handle_give()
        elif card_name == "خد وهات":
            self.needs_wait = True  # تحتاج انتظار المبادلة
            await self._handle_swap_with_player()
        elif card_name == "كعب داير":
            await self._handle_kaab_dayer()
        elif card_name == "بصرة":
            await self._handle_basra()
        elif card_name == "see swap":
            self.needs_wait = True  # تحتاج انتظار الرؤية والمبادلة
            await self._handle_see_swap()
        elif card_name.startswith("-1"):
            await self.channel.send(f"⚠️ {self.player.display_name} لعب -1.")
        elif card_name.startswith("+20"):
            await self.channel.send(f"⚠️ {self.player.display_name} لعب +20.")
        elif "سكرو" in card_name:
            await self.channel.send(f"⚠️ {self.player.display_name} لعب بطاقة سكرو.")
        else:
            await self.channel.send(f"⚠️ {self.player.display_name} لعب بطاقة خاصة.")

    async def _handle_look_other(self, wait_for_view=False):
        other_players = [p for p in self.lobby.players if p != self.player]
        if not other_players:
            return await self.channel.send("❌ مافيش لاعبين تانيين.")
        view = ChoosePlayerView(self.player, self.lobby, action="look_other", timeout=30)
        msg = await self.channel.send(f"🔍 {self.player.display_name} يبحث عن ورقة...", view=view)
        if wait_for_view:
            try:
                await view.wait()
            except Exception:
                pass
            try:
                for child in view.children:
                    child.disabled = True
                await msg.edit(view=view)
            except Exception:
                pass

    async def _handle_look_self(self, wait_for_view=False):
        hand = self.lobby.hands.get(self.player, [])
        if not hand:
            return await self.channel.send(f"❌ {self.player.display_name} معندوش ورق!")
        view = ChooseCardView(self.player, hand, max_select=1, reveal_mode="ephemeral", timeout=30)
        msg = None
        try:
            if self.interaction and not self.interaction.response.is_done():
                await self.interaction.response.send_message("👀 اختار ورقة من إيدك:", view=view, ephemeral=True)
                msg = await self.interaction.original_response()
            else:
                await self.player.send("👀 اختار ورقة من إيدك:", view=view)
        except Exception as e:
            await self.channel.send(f"⚠️ حصل خطأ: {e}")
        if wait_for_view:
            try:
                await view.wait()
            except Exception:
                pass
            try:
                for child in view.children:
                    child.disabled = True
                if msg:
                    await msg.edit(view=view)
            except Exception:
                pass

    async def _handle_give(self):
        interaction_id = f"give_{self.player.id}_{asyncio.get_event_loop().time()}"
        self.lobby.pending_interactions.add(interaction_id)
        
        try:
            view = ChoosePlayerView(self.player, self.lobby, action="give", timeout=25)
            view.interaction_id = interaction_id
            msg = await self.channel.send(f"🎁 {self.player.display_name} يريد إعطاء ورقة...", view=view)
            
            # انتظار انتهاء عملية الإهداء
            try:
                await asyncio.wait_for(view.wait(), timeout=25)
            except asyncio.TimeoutError:
                for child in view.children:
                    child.disabled = True
                await msg.edit(view=view)
                await self.channel.send(f"⏰ انتهى وقت الإهداء لـ {self.player.display_name}")
            
            return view
        finally:
            # التأكد من إزالة الـ ID من الانتظار
            self.lobby.pending_interactions.discard(interaction_id)

    async def _handle_swap_with_player(self):
        await send_webhook_message(f"🔄 {self.player.display_name} بدأ مبادلة (خد وهات)")
        interaction_id = f"swap_{self.player.id}_{asyncio.get_event_loop().time()}"
        self.lobby.pending_interactions.add(interaction_id)
        
        try:
            view = ChoosePlayerView(self.player, self.lobby, action="swap", timeout=25)
            view.interaction_id = interaction_id  # ربط الـ ID بالـ view
            msg = await self.channel.send(f"🔄 {self.player.display_name} يريد مبادلة ورقة...", view=view)
            
            # انتظار انتهاء عملية المبادلة
            try:
                await asyncio.wait_for(view.wait(), timeout=25)
            except asyncio.TimeoutError:
                # إذا انتهى الوقت، نلغي العملية
                for child in view.children:
                    child.disabled = True
                await msg.edit(view=view)
                await self.channel.send(f"⏰ انتهى وقت المبادلة لـ {self.player.display_name}")
            
            return view
        finally:
            # التأكد من إزالة التفاعل من القائمة النشطة
            self.lobby.pending_interactions.discard(interaction_id)

    async def _handle_see_swap(self):
        interaction_id = f"see_swap_{self.player.id}_{asyncio.get_event_loop().time()}"
        self.lobby.pending_interactions.add(interaction_id)
        
        try:
            view = ChoosePlayerView(self.player, self.lobby, action="see_swap", timeout=25)
            view.interaction_id = interaction_id
            msg = await self.channel.send(f"👀 {self.player.display_name} يريد رؤية ومبادلة...", view=view)
            
            # انتظار انتهاء عملية الرؤية والمبادلة
            try:
                await asyncio.wait_for(view.wait(), timeout=25)
            except asyncio.TimeoutError:
                for child in view.children:
                    child.disabled = True
                await msg.edit(view=view)
                await self.channel.send(f"⏰ انتهى وقت الرؤية والمبادلة لـ {self.player.display_name}")
            
            return view
        finally:
            # التأكد من إزالة التفاعل
            self.lobby.pending_interactions.discard(interaction_id)

    async def _handle_kaab_dayer(self):
        view = KaabDayerChooseView(self.player, self.lobby, timeout=30)
        if self.interaction:
            await self.interaction.response.send_message("🎪 كعب داير - اختر:", view=view, ephemeral=True)
        else:
            await self.channel.send("🎪 كعب داير - اختر:", view=view)

    async def _handle_basra(self):
        hand = self.lobby.hands.get(self.player, [])
        if not hand:
            return await self.channel.send(f"❌ {self.player.display_name} معندوش ورق!")
        view = BasraChooseView(self.player, self.lobby, timeout=30)
        if self.interaction:
            await self.interaction.response.send_message("🎯 اختار ورقة للبصرة:", view=view, ephemeral=True)
        else:
            await self.channel.send("🎯 بصرة - اختر:", view=view)

class BasraChooseView(View):
    def __init__(self, player, lobby: Lobby, timeout=30):
        super().__init__(timeout=timeout)
        self.player = player
        self.lobby = lobby
        hand = list(self.lobby.hands.get(player, []))
        for idx, _ in enumerate(hand):
            self.add_item(BasraButton(idx, player, lobby))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class BasraButton(Button):
    def __init__(self, idx, player, lobby: Lobby):
        super().__init__(label=f"🎴 ورقة {idx+1}", style=discord.ButtonStyle.danger)
        self.idx = idx
        self.player = player
        self.lobby = lobby

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        hand = self.lobby.hands.get(self.player, [])
        if not hand or self.idx >= len(hand):
            return await interaction.response.send_message("❌ الورقة مش متاحة!", ephemeral=True)
        removed = hand.pop(self.idx)
        self.lobby.hands[self.player] = hand
        # إرسال الورقة للاعب بشكل خاص
        await send_card(None, removed, title="🗑️ تم التخلص من ورقة", interaction=interaction, ephemeral=True)
        # إرسال رسالة عامة باسم اللاعب وصورة الورقة
        await send_card(self.lobby.channel, removed, title=f"� {self.player.display_name} رمى بصرة وكشف الورقة!")
        remaining = len(hand)
        if remaining == 1:
            self.lobby.scrap_player = self.player
            await self.lobby.channel.send(f"⚠️ {self.player.display_name} بقي معاه ورقة واحدة - سكرو إجباري!")
        elif remaining == 0:
            self.lobby.scrap_player = self.player
            await self.lobby.channel.send(f"🏁 {self.player.display_name} خلص كل كروته! سكرو إجباري 🔥")
        if self.view:
            self.view.stop()

# -----------------------------
# واجهات الاختيار
# -----------------------------
class ChoosePlayerView(View):
    def __init__(self, actor, lobby: Lobby, action: str, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.actor = actor
        self.lobby = lobby
        self.action = action
        self.add_item(PlayerSelect(actor, lobby, action))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class PlayerSelect(Select):
    def __init__(self, actor, lobby: Lobby, action: str):
        options = [discord.SelectOption(label=p.display_name, value=str(p.id)) for p in lobby.players if p != actor]
        super().__init__(placeholder="👥 اختر لاعب", min_values=1, max_values=1, options=options)
        self.actor = actor
        self.lobby = lobby
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.actor:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        if not self.values:
            return await interaction.response.send_message("❌ لم تختار لاعباً.", ephemeral=True)
        target_id = int(self.values[0])
        target = next((p for p in self.lobby.players if p.id == target_id), None)
        if not target:
            return await interaction.response.send_message("❌ اللاعب مش موجود.", ephemeral=True)
        if self.action in ["look_other", "see_swap"]:
            view = TargetCardView(self.actor, target, self.lobby, action=self.action, timeout=30)
            await interaction.response.send_message(f"🔍 اختر ورقة تاخدها من  {target.display_name} :", view=view, ephemeral=True)
        elif self.action == "give":
            view = GiveCardView(self.actor, self.lobby.hands.get(self.actor, []), target, self.lobby, timeout=30)
            await interaction.response.send_message(f"🎁 اختر ورقة لتعطيها لـ {target.display_name}:", view=view, ephemeral=True)
        elif self.action == "swap":
            view = SwapWithPlayerView(self.actor, self.lobby.hands.get(self.actor, []), target, self.lobby, timeout=30)
            await interaction.response.send_message(f"🔄 اختر ورقة من عندك عشان تبدلها مع {target.display_name}:", view=view, ephemeral=True)
        if self.view:
            self.view.stop()

class TargetCardView(View):
    def __init__(self, actor, target, lobby: Lobby, action="look_other", timeout=30):
        super().__init__(timeout=timeout)
        self.actor = actor
        self.target = target
        self.lobby = lobby
        self.action = action
        hand = self.lobby.hands.get(self.target, [])
        for idx, _ in enumerate(hand):
            self.add_item(TargetCardButton(idx, actor, target, lobby, action))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class TargetCardButton(Button):
    def __init__(self, idx, actor, target, lobby: Lobby, action):
        super().__init__(label=f"🎴 ورقة {idx+1}", style=discord.ButtonStyle.primary)
        self.idx = idx
        self.actor = actor
        self.target = target
        self.lobby = lobby
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.actor:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        hand = self.lobby.hands.get(self.target, [])
        if self.idx >= len(hand):
            return await interaction.response.send_message("❌ الورقة غير متاحة.", ephemeral=True)
        card = hand[self.idx]
        if self.action == "look_other":
            await send_card(None, card, title=f"👁️ ورقة {self.target.display_name}", interaction=interaction, ephemeral=True)
        elif self.action == "see_swap":
            view = ConfirmSwapView(self.actor, self.target, self.idx, card, self.lobby, timeout=30)
            await send_card(None, card, title="👀 شوفت ورقة", interaction=interaction, ephemeral=True)
            await interaction.followup.send("🤔 تحب تبدلها مع ورقة من إيدك?", view=view, ephemeral=True)
        if self.view:
            self.view.stop()

class ChooseCardView(View):
    def __init__(self, actor, hand, max_select=1, reveal_mode="ephemeral", timeout=30):
        super().__init__(timeout=timeout)
        self.actor = actor
        self.hand = hand
        self.max_select = max_select
        self.reveal_mode = reveal_mode
        for idx, _ in enumerate(hand):
            self.add_item(ChooseCardButton(idx, actor, hand, self))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class ChooseCardButton(Button):
    def __init__(self, idx, actor, hand, parent_view: ChooseCardView):
        super().__init__(label=f"🎴 ورقة {idx+1}", style=discord.ButtonStyle.primary)
        self.idx = idx
        self.actor = actor
        self.hand = hand
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.actor:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        if self.idx >= len(self.hand):
            return await interaction.response.send_message("❌ الورقة مش متاحة!", ephemeral=True)
        card = self.hand[self.idx]
        # إرسال الورقة للاعب بشكل خاص
        await send_card(None, card, title=f"🎴 ورقتك رقم {self.idx+1}", interaction=interaction, ephemeral=True)
        # إرسال رسالة عامة باسم اللاعب وصورة الورقة
        channel = getattr(self.parent_view, 'channel', None)
        if not channel and hasattr(self.parent_view, 'lobby'):
            channel = getattr(self.parent_view.lobby, 'channel', None)
        if channel:
            await send_card(channel, card, title=f"👁️ {self.actor.display_name} اختار ورقة ليبص عليها")
        if self.view:
            self.view.stop()

class GiveCardView(View):
    def __init__(self, actor, hand, target, lobby: Lobby, timeout=30):
        super().__init__(timeout=timeout)
        self.actor = actor
        self.hand = hand
        self.target = target
        self.lobby = lobby
        for idx, _ in enumerate(list(hand)):
            self.add_item(GiveCardButton(idx, actor, hand, target, lobby))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class GiveCardButton(Button):
    def __init__(self, idx, actor, hand, target, lobby: Lobby):
        super().__init__(label=f"🎴 ورقة {idx+1}", style=discord.ButtonStyle.success)
        self.idx = idx
        self.actor = actor
        self.hand = hand
        self.target = target
        self.lobby = lobby

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.actor:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        if self.idx >= len(self.hand):
            return await interaction.response.send_message("❌ الورقة مش متاحة!", ephemeral=True)
        card = self.hand.pop(self.idx)
        target_hand = self.lobby.hands.get(self.target, [])
        target_hand.append(card)
        self.lobby.hands[self.actor] = self.hand
        self.lobby.hands[self.target] = target_hand
        await interaction.response.send_message(f"✅ اديت ورقة للاعب {self.target.display_name}", ephemeral=True)
        await interaction.channel.send(f"🎁 {self.actor.display_name} ادى ورقة لـ {self.target.display_name}!")
        
        # إزالة التفاعل من قائمة الانتظار
        if hasattr(self.view, 'interaction_id') and self.view.interaction_id:
            self.lobby.pending_interactions.discard(self.view.interaction_id)
        
        if self.view:
            self.view.stop()

class SwapWithPlayerView(View):
    def __init__(self, actor, hand, target, lobby: Lobby, timeout=30):
        super().__init__(timeout=timeout)
        self.actor = actor
        self.hand = hand
        self.target = target
        self.lobby = lobby
        for idx, _ in enumerate(list(hand)):
            self.add_item(SwapWithPlayerButton(idx, actor, target, lobby))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class SwapWithPlayerButton(Button):
    def __init__(self, idx, actor, target, lobby: Lobby):
        super().__init__(label=f"🎴 ورقة {idx+1}", style=discord.ButtonStyle.primary)
        self.idx = idx
        self.actor = actor
        self.target = target
        self.lobby = lobby

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.actor:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        actor_hand = self.lobby.hands.get(self.actor, [])
        target_hand = self.lobby.hands.get(self.target, [])
        if self.idx >= len(actor_hand):
            return await interaction.response.send_message("❌ الورقة مش متاحة!", ephemeral=True)
        if not target_hand:
            return await interaction.response.send_message("❌ اللاعب معندوش ورق!", ephemeral=True)
        view = ChooseTargetCardForSwapView(self.actor, self.target, self.idx, self.lobby, timeout=30)
        await interaction.response.send_message(f"🔄 اختار ورقة من {self.target.display_name}:", view=view, ephemeral=True)
        if self.view:
            self.view.stop()

class ChooseTargetCardForSwapView(View):
    def __init__(self, actor, target, actor_idx, lobby: Lobby, timeout=30):
        super().__init__(timeout=timeout)
        self.actor = actor
        self.target = target
        self.actor_idx = actor_idx
        self.lobby = lobby
        target_hand = self.lobby.hands.get(self.target, [])
        for idx, _ in enumerate(target_hand):
            self.add_item(ChooseTargetCardButton(idx, actor, target, actor_idx, lobby))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

    async def swap_cards(self, actor, target, actor_card_idx, target_card_idx):
        # تنفيذ المبادلة
        actor_hand = self.lobby.hands.get(actor, [])
        target_hand = self.lobby.hands.get(target, [])
        if actor_card_idx >= len(actor_hand) or target_card_idx >= len(target_hand):
            return
        actor_card = actor_hand[actor_card_idx]
        target_card = target_hand[target_card_idx]
        actor_hand[actor_card_idx], target_hand[target_card_idx] = target_card, actor_card
        await send_webhook_message(f"🔁 {actor.display_name} و {target.display_name} تبادلوا أوراق!")

class ChooseTargetCardButton(Button):
    def __init__(self, idx, actor, target, actor_idx, lobby: Lobby):
        super().__init__(label=f"🎴 ورقة {idx+1}", style=discord.ButtonStyle.primary)
        self.idx = idx
        self.actor = actor
        self.target = target
        self.actor_idx = actor_idx
        self.lobby = lobby

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.actor:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        actor_hand = self.lobby.hands.get(self.actor, [])
        target_hand = self.lobby.hands.get(self.target, [])
        if self.actor_idx >= len(actor_hand) or self.idx >= len(target_hand):
            return await interaction.response.send_message("❌ الورقة غير متاحة!", ephemeral=True)
        actor_card = actor_hand[self.actor_idx]
        target_card = target_hand[self.idx]
        actor_hand[self.actor_idx] = target_card
        target_hand[self.idx] = actor_card
        self.lobby.hands[self.actor] = actor_hand
        self.lobby.hands[self.target] = target_hand
        await interaction.response.send_message("✅ تمت المبادلة بنجاح", ephemeral=True)
        await interaction.channel.send(f"🔄 {self.actor.display_name} بدل ورقة مع {self.target.display_name}!")
        
        # إزالة التفاعل من قائمة الانتظار
        if hasattr(self.view, 'interaction_id') and self.view.interaction_id:
            self.lobby.pending_interactions.discard(self.view.interaction_id)
        
        if self.view:
            self.view.stop()

class ConfirmSwapView(View):
    def __init__(self, actor, target, idx, target_card, lobby: Lobby, timeout=30):
        super().__init__(timeout=timeout)
        self.actor = actor
        self.target = target
        self.idx = idx
        self.target_card = target_card
        self.lobby = lobby
        self.add_item(ConfirmTakeButton(actor, target, idx, target_card, lobby))
        self.add_item(ConfirmLeaveButton())
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class ConfirmTakeButton(Button):
    def __init__(self, actor, target, idx, target_card, lobby: Lobby):
        super().__init__(label="✅ خد الورقة", style=discord.ButtonStyle.success)
        self.actor = actor
        self.target = target
        self.idx = idx
        self.target_card = target_card
        self.lobby = lobby

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.actor:
            return await interaction.response.send_message("❌ مش دورك!", ephemeral=True)
        actor_hand = self.lobby.hands.get(self.actor, [])
        target_hand = self.lobby.hands.get(self.target, [])
        if not actor_hand:
            return await interaction.response.send_message("❌ معندكش ورق تبدلها!", ephemeral=True)
        view = ConfirmTakeChooseView(self.actor, self.target, self.idx, self.target_card, self.lobby, timeout=30)
        await interaction.response.send_message("🔄 اختار ورقة لتبديلها:", view=view, ephemeral=True)

class ConfirmTakeChooseView(View):
    def __init__(self, actor, target, target_idx, target_card, lobby: Lobby, timeout=30):
        super().__init__(timeout=timeout)
        self.actor = actor
        self.target = target
        self.target_idx = target_idx
        self.target_card = target_card
        self.lobby = lobby
        hand = self.lobby.hands.get(self.actor, [])
        for idx, _ in enumerate(hand):
            self.add_item(ConfirmTakeChooseButton(idx, actor, target, target_idx, target_card, lobby))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class ConfirmTakeChooseButton(Button):
    def __init__(self, idx, actor, target, target_idx, target_card, lobby: Lobby):
        super().__init__(label=f"🎴 ورقة {idx+1}", style=discord.ButtonStyle.primary)
        self.idx = idx
        self.actor = actor
        self.target = target
        self.target_idx = target_idx
        self.target_card = target_card
        self.lobby = lobby

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.actor:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        actor_hand = self.lobby.hands.get(self.actor, [])
        target_hand = self.lobby.hands.get(self.target, [])
        if self.idx >= len(actor_hand):
            return await interaction.response.send_message("❌ الورقة مش متاحة!", ephemeral=True)
        given_card = actor_hand[self.idx]
        if 0 <= self.target_idx < len(target_hand):
            target_hand[self.target_idx] = given_card
        actor_hand[self.idx] = self.target_card
        self.lobby.hands[self.actor] = actor_hand
        self.lobby.hands[self.target] = target_hand
        await interaction.response.send_message("✅ تمت عملية التبديل", ephemeral=True)
        if self.view:
            self.view.stop()

class ConfirmLeaveButton(Button):
    def __init__(self):
        super().__init__(label="❌ سيبها", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        if self.view:
            self.view.stop()
        await interaction.response.send_message("✅ تم التراجع.", ephemeral=True)

class KaabDayerChooseView(View):
    def __init__(self, player, lobby: Lobby, timeout=30):
        super().__init__(timeout=timeout)
        self.player = player
        self.lobby = lobby
        self.add_item(KaabTwoSelfButton(player, lobby))
        self.add_item(KaabOneEachButton(player, lobby))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class KaabTwoSelfButton(Button):
    def __init__(self, player, lobby: Lobby):
        super().__init__(label="👀 شوف ورقتين من عندك", style=discord.ButtonStyle.primary)
        self.player = player
        self.lobby = lobby

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        hand = self.lobby.hands.get(self.player, [])
        if not hand:
            return await interaction.response.send_message("❌ معندكش ورق!", ephemeral=True)
        dm_view = TwoSelfChoiceView(self.player, self.lobby, timeout=30)
        await interaction.response.send_message("👀 اختار ورقتين لعرضهم:", view=dm_view, ephemeral=True)
        if self.view:
            self.view.stop()

class TwoSelfChoiceView(View):
    def __init__(self, player, lobby: Lobby, timeout=30):
        super().__init__(timeout=timeout)
        self.player = player
        self.lobby = lobby
        self.chosen = 0
        hand = self.lobby.hands.get(self.player, [])
        for idx, _ in enumerate(hand):
            self.add_item(TwoSelfCardButton(idx, self.player, self.lobby, self))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class TwoSelfCardButton(Button):
    def __init__(self, idx, player, lobby: Lobby, parent_view: TwoSelfChoiceView):
        super().__init__(label=f"🎴 ورقة {idx+1}", style=discord.ButtonStyle.primary)
        self.idx = idx
        self.player = player
        self.lobby = lobby
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        hand = self.lobby.hands.get(self.player, [])
        if self.idx >= len(hand):
            return await interaction.response.send_message("❌ الورقة مش متاحة!", ephemeral=True)
        try:
            card = hand[self.idx]
            await send_card(None, card, title=f"🎴 ورقة {self.idx+1}", interaction=interaction, ephemeral=True)
            self.parent_view.chosen += 1
            if self.parent_view.chosen >= 2:
                self.parent_view.stop()
        except Exception as e:
            logger.error(f"Error in card button callback for player {self.player}: {str(e)}")
            await interaction.response.send_message("❌ حدث خطأ في عرض الورقة!", ephemeral=True)

class KaabOneEachButton(Button):
    def __init__(self, player, lobby: Lobby):
        super().__init__(label="👥 شوف ورقة من كل لاعب", style=discord.ButtonStyle.primary)
        self.player = player
        self.lobby = lobby

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        others = [p for p in self.lobby.players if p != self.player]
        if not others:
            return await interaction.response.send_message("❌ مافيش لاعبين تانيين.", ephemeral=True)
        await interaction.response.send_message("🔒 أرسلت لك واجهات اختيار خاصة لكل لاعب:", ephemeral=True)
        for p in others:
            hand = self.lobby.hands.get(p, [])
            if not hand:
                continue
            chooser = OneEachView(self.player, self.lobby, target=p, timeout=30)
            await interaction.followup.send(f"👀 اختار ورقة من {p.display_name}:", view=chooser, ephemeral=True)
        if self.view:
            self.view.stop()

class OneEachView(View):
    def __init__(self, actor, lobby: Lobby, target: discord.Member, timeout=30):
        super().__init__(timeout=timeout)
        self.actor = actor
        self.lobby = lobby
        self.target = target
        hand = self.lobby.hands.get(target, [])
        for idx, _ in enumerate(hand):
            self.add_item(OneEachCardButton(idx, actor, lobby, target, self))
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class OneEachCardButton(Button):
    def __init__(self, idx, actor, lobby: Lobby, target: discord.Member, parent_view):
        super().__init__(label=f"🎴 ورقة {idx+1}", style=discord.ButtonStyle.primary)
        self.idx = idx
        self.actor = actor
        self.lobby = lobby
        self.target = target
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.actor:
            return await interaction.response.send_message("❌ مش من حقك!", ephemeral=True)
        hand = self.lobby.hands.get(self.target, [])
        if self.idx >= len(hand):
            return await interaction.response.send_message("❌ الورقة غير متاحة!", ephemeral=True)
        card = hand[self.idx]
        await send_card(None, card, title=f"👁️ {self.target.display_name} - ورقة {self.idx+1}", interaction=interaction, ephemeral=True)
        try:
            self.parent_view.stop()
        except Exception:
            pass

# -----------------------------
# نظام بدء الجولة
# -----------------------------
async def start_round(channel: discord.TextChannel, lobby: Lobby):
    # التحقق من إيقاف اللعبة
    if lobby.is_stopped:
        return
    

    random.shuffle(lobby.players)
    if getattr(lobby, 'team_mode', False) and len(lobby.players) >= 4:
        # تقسيم تلقائي لفريقين
        mid = len(lobby.players) // 2
        team1 = lobby.players[:mid]
        team2 = lobby.players[mid:]
        lobby.teams = [team1, team2]
        # ترتيب الأدوار بحيث لا يأتي لاعبان من نفس الفريق ورا بعض
        ordered_players = []
        t1 = team1.copy()
        t2 = team2.copy()
        while t1 or t2:
            if t1:
                ordered_players.append(t1.pop(0))
            if t2:
                ordered_players.append(t2.pop(0))
        lobby.players = ordered_players
        start_embed = discord.Embed(
            title="🎉 بداية مود التيمات!",
            description="**تم تقسيم اللاعبين إلى فريقين!**",
            color=0x00bfff
        )
        start_embed.add_field(
            name="🔵 الفريق 1",
            value="\n".join(format_member(p) for p in team1),
            inline=True
        )
        start_embed.add_field(
            name="🟢 الفريق 2",
            value="\n".join(format_member(p) for p in team2),
            inline=True
        )
        start_embed.set_footer(text="استعدوا للمغامرة! (مود التيمات)")
        await channel.send(embed=start_embed)
    else:
        start_embed = discord.Embed(
            title="🎉 بداية اللعبة!",
            description="**تم بدء لعبة سكرو بنجاح!** 🚀",
            color=0x2ecc71
        )
        start_embed.add_field(
            name="👥 اللاعبين",
            value=", ".join(format_member(p) for p in lobby.players),
            inline=False
        )
        start_embed.set_footer(text="استعدوا للمغامرة!")
        await channel.send(embed=start_embed)
    
    card_view_embed = discord.Embed(
        title="🃏 مرحلة مشاهدة الأوراق",
        description="**كل لاعب لديه 20 ثانية لمشاهدة ورقتين من أصل 4 أوراق!**",
        color=0x9b59b6
    )
    card_view_embed.add_field(name="⏰ المدة", value="20 ثانية لكل لاعب", inline=True)
    card_view_embed.add_field(name="🎴 المسموح", value="ورقتين فقط من أصل 4", inline=True)
    card_view_embed.set_footer(text="الوقت المتبقي: 20 ثانية")
    
    view = PlayerSelectionView(lobby)
    msg = await channel.send(embed=card_view_embed, view=view)
    view.message = msg
    lobby.current_draw_view = view
    lobby.current_draw_msg = msg
    
    for i in range(20, 0, -1):
        await asyncio.sleep(1)
        # التحقق من إيقاف اللعبة
        if lobby.is_stopped:
            for child in view.children:
                child.disabled = True
            stopped_embed = discord.Embed(
                title="🛑 تم إيقاف اللعبة",
                description="**تم إيقاف اللعبة بواسطة المشرف**",
                color=0xe74c3c
            )
            await msg.edit(embed=stopped_embed, view=view)
            return
        try:
            card_view_embed.set_footer(text=f"الوقت المتبقي: {i} ثانية")
            await msg.edit(embed=card_view_embed, view=view)
        except Exception:
            pass

    for child in view.children:
        child.disabled = True
    
    timeout_embed = discord.Embed(
        title="⏰ انتهى وقت المشاهدة",
        description="**انتهى وقت مشاهدة الأوراق للجميع**",
        color=0xf39c12
    )
    await msg.edit(embed=timeout_embed, view=view)
    
    if not lobby.deck:
        # deck لم يتم إنشاؤه بعد
        lobby.deck = create_full_deck(getattr(lobby, 'team_mode', False))
    if lobby.deck:
        first_card = lobby.deck.pop()
        lobby.ground.append(first_card)
        ground_embed = discord.Embed(title="🎴 أول ورقة على الأرض", description="**تم وضع الورقة الأولى على الأرض:**", color=0x3498db)
        await channel.send(embed=ground_embed)
        await send_card(channel, first_card, title="أول ورقة على الأرض")
    
    start_play_embed = discord.Embed(title="🚀 بدء الأدوار!", description="**بدأت أدوار اللاعبين...**", color=0x2ecc71)
    await channel.send(embed=start_play_embed)

    max_rounds = 50  # حد أقصى للجولات لمنع اللوب اللانهائي
    
    while lobby.round_number < max_rounds:
        # التحقق من إيقاف اللعبة في بداية كل جولة
        if lobby.is_stopped:
            await channel.send("🛑 تم إيقاف اللعبة بواسطة المشرف.")
            lobby.cleanup_lobby()
            active_lobbies.pop(channel.id, None)
            return

        # التحقق من نهاية اللعبة - لو مافيش أوراق متاحة
        if not lobby.deck and (not lobby.ground or len(lobby.ground) <= 1):
            await channel.send("⚠️ انتهت اللعبة! (مافيش كروت للسحب).")
            await show_end_game_summary(lobby, channel)
            lobby.cleanup_lobby()
            active_lobbies.pop(channel.id, None)
            return

        skip_next = getattr(lobby, '_skip_next_turn', False)
        players_list = list(lobby.players)
        i = 0
        while i < len(players_list):
            player = players_list[i]
            # تهيئة عداد AFK للاعب إذا لم يوجد
            if player not in lobby.afk_counter:
                lobby.afk_counter[player] = 0
            # تنفيذ السكيب لو مطلوب
            if skip_next:
                lobby.afk_counter[player] += 1
                if lobby.afk_counter[player] >= 2:
                    await channel.send(f"🚫 {player.display_name} تم طرده تلقائياً بسبب عدم اللعب لدورين متتاليين!")
                    lobby.players.remove(player)
                    del lobby.afk_counter[player]
                    players_list = list(lobby.players)
                    # لا تزود i لأن اللاعب الحالي تم حذفه
                    skip_next = False
                    lobby._skip_next_turn = False
                    continue
                else:
                    await channel.send(f"⏭️ تم تخطي دور {player.display_name} بسبب كرت بينج/بونج! (تحذير: إذا لم تلعب في الدور القادم سيتم طردك)")
                    skip_next = False
                    lobby._skip_next_turn = False
                    i += 1
                    continue
            # ...existing code for each player's turn...
            # التحقق من إيقاف اللعبة قبل كل دور
            if lobby.is_stopped:
                await channel.send("🛑 تم إيقاف اللعبة بواسطة المشرف.")
                lobby.cleanup_lobby()
                active_lobbies.pop(channel.id, None)
                return
            # فحص عدد اللاعبين - إنهاء اللعبة لو بقى لاعب واحد أو أقل
            if len(lobby.players) <= 1:
                end_embed = discord.Embed(
                    title="🛑 إنهاء اللعبة تلقائياً",
                    description="**تم إنهاء اللعبة لعدم وجود لاعبين كافيين!**\n\nيحتاج على الأقل لاعبين 2 لمتابعة اللعب.",
                    color=0xe74c3c
                )
                if lobby.players:
                    end_embed.add_field(
                        name="👤 اللاعب المتبقي",
                        value=format_member(lobby.players[0]),
                        inline=False
                    )
                    end_embed.add_field(
                        name="🏆 النتيجة",
                        value=f"**{lobby.players[0].display_name}** فاز بشكل افتراضي!",
                        inline=False
                    )
                await channel.send(embed=end_embed)
                lobby.cleanup_lobby()
                active_lobbies.pop(channel.id, None)
                return
            # شرط انتهاء اللعبة - لو لاعب أعلن سكرو ورجع دوره
            if lobby.scrap_player and player == lobby.scrap_player:
                await channel.send(f"🏁 اللعبة انتهت! {player.display_name} كان معلن سكرو.")
                await show_end_game_summary(lobby, channel)
                lobby.cleanup_lobby()
                active_lobbies.pop(channel.id, None)
                return
            # التحقق من الأوراق المتبقية للاعب
            player_hand = lobby.hands.get(player, [])
            if len(player_hand) == 0:
                await channel.send(f"🏆 {player.display_name} خلص كل كروته! انتهت اللعبة!")
                await show_end_game_summary(lobby, channel)
                lobby.cleanup_lobby()
                active_lobbies.pop(channel.id, None)
                return
            # إعادة تعبئة الديك لو فضى
            if not lobby.deck:
                refilled = refill_deck_from_ground(lobby)
                if not refilled and (not lobby.ground or len(lobby.ground) <= 1):
                    await channel.send("⚠️ انتهت اللعبة! (الديك خلص).")
                    await show_end_game_summary(lobby, channel)
                    lobby.cleanup_lobby()
                    active_lobbies.pop(channel.id, None)
                    return
            lobby.current_turn_player = player
            # ...existing code for player's turn...
            # عند تفاعل اللاعب (لعب أو سحب ورقة)، صفر عداد AFK
            lobby.afk_counter[player] = 0
            i += 1
            await channel.send(f"🎯 **الدور الحالي:** {player.mention}")
            hand = lobby.hands.get(player, [])
            draw_view = DrawCardView(player, lobby.deck, hand, lobby)
            draw_msg = await channel.send(
                f"{player.mention} دورك! اضغط اسحب أو استخدم الأزرار. ⏰ (30 ثانية)",
                view=draw_view
            )
            draw_view.message = draw_msg
            lobby.current_draw_view = draw_view
            lobby.current_draw_msg = draw_msg

            try:
                await asyncio.wait_for(draw_view.wait(), timeout=30)
            except asyncio.TimeoutError:
                # لو اللاعب مرد في الوقت، نسحب ورقة أوتوماتيك ونرميها
                timeout_embed = discord.Embed(
                    title="⏰ انتهى وقت الدور",
                    description=f"**انتهى وقت {player.display_name}** - سحب تلقائي ورمي",
                    color=0xf39c12
                )
                await channel.send(embed=timeout_embed)
                
                # سحب ورقة تلقائياً
                if lobby.deck:
                    auto_card = lobby.deck.pop()
                    lobby.ground.append(auto_card)
                    await channel.send(f"🤖 تم سحب ورقة تلقائياً لـ {player.display_name} ورميها على الأرض")
                
                logger.warning(f"Player {player.display_name} timed out during turn")
            finally:
                # تنظيف الـ view
                try:
                    for child in draw_view.children:
                        child.disabled = True
                    if draw_msg:
                        await draw_msg.edit(view=draw_view)
                except Exception:
                    pass

            lobby.current_turn_player = None
            lobby.hands[player] = hand
            await asyncio.sleep(1)

        lobby.round_number += 1
        
        # رسالة بداية الجولة الجديدة (إلا إذا وصلنا الحد الأقصى)
        if lobby.round_number < max_rounds:
            await channel.send(f"🔄 **الجولة {lobby.round_number} ابتدت!**")
    
    # لو وصلنا للحد الأقصى من الجولات
    await channel.send(f"⏰ وصلنا للحد الأقصى من الجولات ({max_rounds})! انتهت اللعبة.")
    await show_end_game_summary(lobby, channel)
    lobby.cleanup_lobby()
    active_lobbies.pop(channel.id, None)

# -----------------------------
# نظام البوت الرئيسي
# -----------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower().strip()
    if content == "سكرووو صاحب صحبه":
        # التحقق من الشراء أولاً
        guild_id = message.guild.id if message.guild else 0
        user_id = message.author.id
        
        # الأونر والـ VIP يمكنهم اللعب بدون شراء
        if not (is_owner(message.author) or is_vip(message.author) or has_purchased(guild_id, user_id, "teams_mode")):
            locked_embed = discord.Embed(
                title="🔒 مود مقفل",
                description="**مود صاحب صحبه غير متاح لك!**\n\nيجب شراء هذا المود للعب به.",
                color=0xe74c3c
            )
            locked_embed.add_field(
                name="💰 السعر",
                value="50 نقطة",
                inline=True
            )
            
            # عرض نقاط اللاعب
            stats = points_manager.get_user_stats(guild_id, user_id)
            current_points = int(stats.get("points", 0))
            locked_embed.add_field(
                name="💳 نقاطك",
                value=f"{current_points} نقطة",
                inline=True
            )
            
            locked_embed.add_field(
                name="🛒 كيفية الشراء",
                value="استخدم الأمر: `/شراء`",
                inline=False
            )
            
            if current_points < 50:
                locked_embed.add_field(
                    name="📉 النقص",
                    value=f"تحتاج {50 - current_points} نقطة إضافية",
                    inline=False
                )
            
            locked_embed.set_footer(text="العب المزيد من الألعاب لكسب نقاط!")
            return await message.channel.send(embed=locked_embed)
        
        # حارس منع التكرار عبر العمليات (قفل ملف حسب Message ID)
        locks_dir = Path(__file__).parent / "locks"
        try:
            locks_dir.mkdir(exist_ok=True)
        except Exception:
            pass
        lock_file = locks_dir / f"msg_{message.id}.lock"
        try:
            lock_file.touch(exist_ok=False)
        except FileExistsError:
            # تم التعامل مع هذه الرسالة بواسطة عملية أخرى
            return

        if message.channel.id in active_lobbies:
            error_embed = discord.Embed(title="❌ لعبة نشطة", description="يوجد لعبة نشطة بالفعل في هذه القناة!", color=0xe74c3c)
            return await message.channel.send(embed=error_embed)

        # إنشاء lobby مع team_mode
        lobby = Lobby(message.channel, team_mode=True)
        active_lobbies[message.channel.id] = lobby
        holder = {}
        join_view = JoinView(lobby, holder)
        
        # إنشاء embed مع تايمر
        embed = discord.Embed(
            title="🎮 مود التيمات (Teams Mode)",
            description="**انضم للعبة! سيتم تقسيمكم تلقائياً إلى فرق متساوية** 🤝\n\n• الحد الأدنى: 4 لاعبين\n• التقسيم: تلقائي (2v2، 3v3، أو 4v4)",
            color=0x00bfff
        )
        embed.add_field(name="⏰ وقت الانضمام", value="**20 ثانية**", inline=True)
        embed.add_field(name="👥 اللاعبين", value="**0 / 8**", inline=True)
        embed.set_footer(text="⏱️ العد التنازلي: 20 ثانية")
        
        join_msg = await message.channel.send(embed=embed, view=join_view)
        holder['msg'] = join_msg
        lobby.join_view = join_view
        lobby.join_msg = join_msg

        # العد التنازلي 20 ثانية (مثل المود العادي تماماً)
        for i in range(20, 0, -1):
            await asyncio.sleep(1)
            if lobby.is_stopped:
                break
            try:
                # تحديث الـ embed مع العد التنازلي
                embed = discord.Embed(
                    title="🎮 مود التيمات (Teams Mode)",
                    description="**انضم للعبة! سيتم تقسيمكم تلقائياً إلى فرق متساوية** 🤝\n\n• الحد الأدنى: 4 لاعبين\n• التقسيم: تلقائي (2v2، 3v3، أو 4v4)",
                    color=0x00bfff
                )
                embed.add_field(name="⏰ وقت الانضمام", value=f"**{i} ثانية**", inline=True)
                embed.add_field(name="👥 اللاعبين", value=f"**{len(lobby.players)} / 8**", inline=True)
                
                # قائمة اللاعبين
                if lobby.players:
                    players_list = "\n".join([f"• {format_member(p)}" for p in lobby.players])
                    embed.add_field(name="🎯 قائمة اللاعبين", value=players_list, inline=False)
                
                embed.set_footer(text=f"⏱️ العد التنازلي: {i} ثانية")
                await join_msg.edit(embed=embed, view=join_view)
            except Exception:
                pass

        try:
            join_view.stop()
            final_embed = discord.Embed(
                title="⏰ انتهى وقت الانضمام", 
                description="**انتهى وقت الانضمام للعبة - Teams Mode**", 
                color=0xf39c12
            )
            await join_msg.edit(embed=final_embed, view=None)
        except Exception:
            pass

        # التحقق من عدد اللاعبين (4 على الأقل لمود التيمات)
        if len(lobby.players) < 4:
            error_embed = discord.Embed(
                title="❌ عدد غير كافي",
                description="**مود التيمات يحتاج على الأقل 4 لاعبين لبدء اللعبة!**\n\nيجب أن يكون العدد زوجياً للتقسيم العادل (4, 6, أو 8 لاعبين)",
                color=0xe74c3c
            )
            await message.channel.send(embed=error_embed)
            active_lobbies.pop(message.channel.id, None)
            return

        # إعلان تقسيم الفرق
        teams_announcement = discord.Embed(
            title="🎮 تقسيم الفرق",
            description="**جاري تقسيم اللاعبين إلى فرق...**",
            color=0x3498db
        )
        await message.channel.send(embed=teams_announcement)
        
        # بدء اللعبة
        lobby.deck = create_full_deck(team_mode=True)
        deal_hands(lobby)
        await start_round(message.channel, lobby)
        return
    if content == "سكرووو":
        # حارس منع التكرار عبر العمليات (قفل ملف حسب Message ID)
        locks_dir = Path(__file__).parent / "locks"
        try:
            locks_dir.mkdir(exist_ok=True)
        except Exception:
            pass
        lock_file = locks_dir / f"msg_{message.id}.lock"
        try:
            lock_file.touch(exist_ok=False)
        except FileExistsError:
            return

        if message.channel.id in active_lobbies:
            error_embed = discord.Embed(title="❌ لعبة نشطة", description="يوجد لعبة نشطة بالفعل في هذه القناة!", color=0xe74c3c)
            return await message.channel.send(embed=error_embed)

        lobby = Lobby(message.channel)
        active_lobbies[message.channel.id] = lobby
        holder = {}
        join_view = JoinView(lobby, holder)
        embed = generate_lobby_embed(lobby, countdown=20)
        join_msg = await message.channel.send(embed=embed, view=join_view)
        holder['msg'] = join_msg
        lobby.join_view = join_view
        lobby.join_msg = join_msg

        for i in range(20, 0, -1):
            await asyncio.sleep(1)
            if lobby.is_stopped:
                break
            try:
                await join_msg.edit(embed=generate_lobby_embed(lobby, countdown=i), view=join_view)
            except Exception:
                pass

        try:
            join_view.stop()
            final_embed = discord.Embed(title="⏰ انتهى وقت الانضمام", description="**انتهى وقت الانضمام للعبة**", color=0xf39c12)
            await join_msg.edit(embed=final_embed, view=None)
        except Exception:
            pass

        if len(lobby.players) < 2:
            error_embed = discord.Embed(title="❌ عدد غير كافي", description="يحتاج على الأقل 2 لاعبين لبدء اللعبة!", color=0xe74c3c)
            await message.channel.send(embed=error_embed)
            active_lobbies.pop(message.channel.id, None)
            return

        lobby.deck = create_full_deck()
        deal_hands(lobby)
        await start_round(message.channel, lobby)

    await bot.process_commands(message)

# -----------------------------
# الأوامر الجديدة
# -----------------------------
def _build_points_embed(target: discord.Member, stats: dict) -> discord.Embed:
    games = int(stats.get("games", 0))
    wins = int(stats.get("wins", 0))
    points = int(stats.get("points", 0))
    best = stats.get("best")
    total_score = int(stats.get("total_score", 0))
    avg = (total_score / games) if games > 0 else 0.0

    embed = discord.Embed(
        title=f"📊 نقاط وإحصائيات — {target.display_name}",
        color=0x3498db
    )
    embed.add_field(name="🏅 النقاط", value=f"{points}", inline=True)
    embed.add_field(name="🎮 عدد الألعاب", value=f"{games}", inline=True)
    embed.add_field(name="🥇 مرات الفوز", value=f"{wins}", inline=True)
    embed.add_field(name="🔻 أفضل نتيجة (أقل)", value=(str(best) if best is not None else "—"), inline=True)
    embed.add_field(name="📉 متوسط النتيجة", value=f"{avg:.2f}", inline=True)
    embed.set_footer(text="ملاحظة: الأقل نقاطاً داخل الجولة أفضل ✨")
    return embed
@bot.command(name="نقط")
async def my_points(ctx, member: Optional[discord.Member] = None):
    """عرض نقاطك المحفوظة وإحصاءاتك. استخدم: !نقط [@شخص]"""
    target = member or ctx.author
    guild_id = ctx.guild.id if ctx.guild else 0
    stats = points_manager.get_user_stats(guild_id, target.id)
    await ctx.send(embed=_build_points_embed(target, stats))

# -----------------------------
# أوامر اقتصادية للأونر
# -----------------------------
@bot.command(name="reward")
async def cmd_gift_points(ctx, member: discord.Member, points: int):
    """🎁 إهداء نقاط (Owner فقط) — استخدام: !reward @member <1-10>"""
    if not is_owner(ctx.author):
        return await ctx.send("❌ هذا الأمر للأونر فقط! 👑", delete_after=5)
    if points < 1 or points > 10:
        return await ctx.send("❌ عدد النقاط يجب أن يكون بين 1-10", delete_after=5)
    guild_id = ctx.guild.id if ctx.guild else 0
    points_manager.add_points(guild_id, member.id, points)
    try:
        await send_webhook_message(f"🎁 {ctx.author.display_name} أهدى {points} نقطة لـ {member.display_name}")
    except Exception:
        pass
    try:
        await _init_sync_client()
        await _safe_call(
            sync_client.update_points(
                guild_id,
                member.id,
                points=points,
                wins=0,
                games=0,
                score=None,
                mode="inc",
            ),
            ctx=f"update_points:gift:user={member.id}:+{points}",
        )
    except Exception:
        pass
    gift_embed = discord.Embed(
        title="🎁 هدية من الأونر!",
        description=f"**👑 {ctx.author.mention} أهدى {points} نقطة لـ {format_member(member)}!**",
        color=0xFFD700
    )
    await ctx.send(embed=gift_embed)


# أمر top/توب/توب. كأمر عادي (prefix) مع دعم كل البريفكسات، ويعرض المتصدرين بشكل رسومي
@bot.command(name="top", aliases=["توب", ".top", ".توب"])
async def top_command(ctx):
    """عرض أفضل 10 لاعبين في السيرفر بشكل رسومي"""
    guild_id = ctx.guild.id if ctx.guild else 0
    try:
        guild_data = points_manager.data.get(str(guild_id), {})
        players_stats = []
        for user_id, stats in guild_data.items():
            try:
                user = ctx.guild.get_member(int(user_id))
                if user:
                    players_stats.append({
                        'user': user,
                        'points': int(stats.get('points', 0)),
                        'games': int(stats.get('games', 0)),
                        'wins': int(stats.get('wins', 0))
                    })
            except Exception:
                continue
        players_stats.sort(key=lambda x: x['points'], reverse=True)
        leaderboard_embed = discord.Embed(
            title="🏆 لوحة المتصدرين - سكرو",
            description="**أفضل 10 لاعبين في السيرفر:**",
            color=0xFFD700
        )
        if players_stats:
            for i, player in enumerate(players_stats[:10], 1):
                emoji = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                crown = " 👑" if is_owner(player['user']) else ""
                bar = "█" * min(player['points']//5, 15) + "░" * (15 - min(player['points']//5, 15))
                leaderboard_embed.add_field(
                    name=f"{emoji} #{i} {player['user'].display_name}{crown}",
                    value=f"`{bar}`\n💰 **{player['points']}** نقطة | 🎮 {player['games']} | 🏆 {player['wins']}",
                    inline=False
                )
        else:
            leaderboard_embed.add_field(name="📊 لا توجد بيانات", value="لم يلعب أحد بعد!", inline=False)
        leaderboard_embed.set_footer(text=f"📊 إجمالي اللاعبين المسجلين: {len(players_stats)}")
        msg = await ctx.send(embed=leaderboard_embed)
        # حذف بعد 30 ثانية لتقليل الازدحام
        await asyncio.sleep(30)
        try:
            await msg.delete()
            await ctx.message.delete()
        except:
            pass
    except Exception as e:
        await ctx.send("❌ حدث خطأ في جلب البيانات!", delete_after=5)

# أمر السلاش يبقى كما هو (لمن يريد استخدامه من السلاش)

@bot.command(name="setpoints")
async def cmd_set_points(ctx, member: discord.Member, points: int):
    """تعديل نقاط عضو مباشرة - أونر فقط"""
    if not is_owner(ctx.author):
        return await ctx.send("❌ هذا الأمر للأونر فقط! 👑", delete_after=5)
    guild_id = ctx.guild.id if ctx.guild else 0
    
    # تحديث النقاط مباشرة
    current_stats = points_manager.get_user_stats(guild_id, member.id)
    current_stats['points'] = points
    
    # حفظ التغييرات
    points_manager._ensure_user(guild_id, member.id)
    points_manager.data[str(guild_id)][str(member.id)]['points'] = points
    points_manager._save()
    try:
        await send_webhook_message(f"⚙️ {ctx.author.display_name} عدل نقاط {member.display_name} إلى {points}")
    except Exception:
        pass
    # مزامنة النقاط للموقع (تعيين قيمة)
    try:
        await _init_sync_client()
        await _safe_call(
            sync_client.update_points(
                guild_id,
                member.id,
                points=points,
                wins=0,
                games=0,
                score=None,
                mode="set",
            ),
            ctx=f"update_points:set:user={member.id}:{points}",
        )
        logger.info(f"Synced points (set) -> guild={guild_id}, user={member.id}, points={points}")
    except Exception as e:
        logger.error(f"Points sync (set) failed: {e}")
    set_embed = discord.Embed(
        title="👑 تم تعديل النقاط",
        description=f"**تم تحديث نقاط {format_member(member)} إلى {points} نقطة**",
        color=0xFFD700
    )
    await ctx.send(embed=set_embed)

@bot.command(name="vip")
async def cmd_manage_vip(ctx, action: str, member: Optional[discord.Member] = None, *, tier: Optional[str] = None):
    """👑 إدارة VIP — استخدام: !vip <add|remove|list|check> [@member] [tier]"""
    if not is_owner(ctx.author):
        return await ctx.send("❌ هذا الأمر حصري للأونر فقط! 👑", delete_after=5)
    action = action.lower()
    if action == "add":
        if not member or not tier:
            return await ctx.send("❌ حدد العضو ودرجة VIP!", delete_after=5)
        await send_webhook_message(f"👑 تمت إضافة VIP: {member.display_name} - {tier} بواسطة {ctx.author.display_name}")
        VIP_MEMBERS[member.id] = tier
        save_vip_members(VIP_MEMBERS)
        try:
            await _init_sync_client()
            await _safe_call(sync_client.set_vip(member.id, tier), ctx=f"set_vip:add:{member.id}:{tier}")
        except Exception:
            pass
        vip_icon = "💎" if "Diamond" in tier else "🌟" if "Gold" in tier else "⭐" if "Silver" in tier else "🎖️"
        embed = discord.Embed(
            title=f"{vip_icon} تم منح VIP!",
            description=f"**{format_member(member)}** أصبح الآن **{tier}**!",
            color=get_vip_embed_color(member)
        )
        return await ctx.send(embed=embed)
    elif action == "remove":
        if not member:
            return await ctx.send("❌ حدد العضو المراد إزالته!", delete_after=5)
        await send_webhook_message(f"❌ تم إزالة VIP: {member.display_name} بواسطة {ctx.author.display_name}")
        if member.id in VIP_MEMBERS:
            old_tier = VIP_MEMBERS.pop(member.id)
            save_vip_members(VIP_MEMBERS)
            try:
                await _init_sync_client()
                await _safe_call(sync_client.set_vip(member.id, None), ctx=f"set_vip:remove:{member.id}")
            except Exception:
                pass
            embed = discord.Embed(
                title="❌ تم إلغاء VIP",
                description=f"**{member.mention}** لم يعد **{old_tier}**",
                color=0x95a5a6
            )
            return await ctx.send(embed=embed)
        else:
            return await ctx.send(f"❌ {member.mention} ليس عضو VIP!", delete_after=5)
    elif action == "list":
        if not VIP_MEMBERS:
            embed = discord.Embed(title="📋 قائمة VIP", description="لا يوجد أعضاء VIP حالياً", color=0x95a5a6)
        else:
            embed = discord.Embed(title="📋 قائمة أعضاء VIP", color=0xFFD700)
            vip_lines = []
            guild = ctx.guild
            for user_id, tier in VIP_MEMBERS.items():
                vip_icon = "💎" if "Diamond" in tier else "🌟" if "Gold" in tier else "⭐" if "Silver" in tier else "🎖️"
                name = None
                if guild:
                    try:
                        user = guild.get_member(int(user_id))
                        if not user:
                            user = await guild.fetch_member(int(user_id))
                        if user:
                            name = user.display_name
                    except Exception:
                        name = None
                vip_lines.append(f"{vip_icon} **{name or 'User ' + str(user_id)}** - {tier}")
            embed.description = "\n".join(vip_lines) if vip_lines else "لا يوجد أعضاء VIP متاحين في هذا السيرفر"
        return await ctx.send(embed=embed)
    elif action == "check":
        if not member:
            return await ctx.send("❌ حدد العضو للفحص!", delete_after=5)
        if is_vip(member):
            tier = get_vip_tier(member)
            vip_icon = "💎" if "Diamond" in tier else "🌟" if "Gold" in tier else "⭐" if "Silver" in tier else "🎖️"
            embed = discord.Embed(
                title=f"{vip_icon} عضو VIP",
                description=f"**{member.display_name}** هو **{tier}**",
                color=get_vip_embed_color(member)
            )
        else:
            embed = discord.Embed(
                title="👤 عضو عادي",
                description=f"**{member.display_name}** عضو عادي (غير VIP)",
                color=0x95a5a6
            )
        return await ctx.send(embed=embed)
    else:
        return await ctx.send("❌ استخدم: !vip <add|remove|list|check> ...", delete_after=5)

# -----------------------------
# Professional Slash Commands
# -----------------------------
@bot.tree.command(name="help", description="📖 View game commands and rules")
async def help_command(interaction: discord.Interaction):
    """عرض دليل الأوامر والقواعد"""
    help_embed = discord.Embed(
        title="🎴 Screw Card Game - Commands Guide",
        description="**Welcome to Screw Card Game!** Here are all available commands:",
        color=0x3498db
    )
    
    # أوامر عامة
    help_embed.add_field(
        name="🎮 Game Commands",
        value="""
        `/screw` - Start new game
        `/end` - Stop current game (Admin)
        `/stats [@member]` - View player stats
        `/top` - Server leaderboard
        """,
        inline=True
    )
    
    # أوامر الأونر (لن تظهر في السلاش لغير المشرفين بحكم الصلاحيات الافتراضية)
    if is_owner(interaction.user):
        help_embed.add_field(
            name="👑 Owner Commands",
            value="""
            `/control` - Owner panel
            `/reward @member <points>` - Gift points
            `/setpoints @member <points>` - Set points
            `/owners add|remove|list` - Manage owners
            """,
            inline=True
        )
    
    # معلومات اللعبة
    help_embed.add_field(
        name="📋 Game Info",
        value="""
        • Type `سكرووو` to start
        • 2-8 players per game
        • Goal: Lowest points wins
        • Use `!شرح` for detailed rules
        """,
        inline=False
    )
    
    help_embed.set_footer(text="🎯 Pro tip: Type 'سكرووو' in any channel to start a game!")
    await interaction.response.send_message(embed=help_embed, ephemeral=True)

@bot.tree.command(name="info", description="ℹ️ Bot information and server stats")
async def info_command(interaction: discord.Interaction):
    """معلومات البوت والسيرفر"""
    guild_count = len(bot.guilds) if bot.guilds else 1
    active_games = len(active_lobbies)
    
    info_embed = discord.Embed(
        title="ℹ️ Bot Information",
        description="**Screw Card Game Bot** - Advanced multiplayer card game experience",
        color=0x9b59b6
    )
    
    info_embed.add_field(
        name="📊 Statistics",
        value=f"""
        🌐 **Servers:** {guild_count}
        🎮 **Active Games:** {active_games}
        👥 **Users:** {len(interaction.guild.members) if interaction.guild else 'N/A'}
        """,
        inline=True
    )
    
    info_embed.add_field(
        name="🔧 Features",
        value="""
        ✅ Persistent points system
        ✅ Interactive UI & buttons
        ✅ Real-time game mechanics
        ✅ Professional slash commands
        ✅ Owner privileges system
        """,
        inline=True
    )
    
    # تمييز خاص للأونر
    if is_owner(interaction.user):
        info_embed.add_field(
            name="👑 Owner Status",
            value="**Verified Bot Owner** ✨\nAccess to advanced controls",
            inline=False
        )
    
    info_embed.set_footer(text="Made with ❤️ for Discord gaming communities")
    # رابط الداش بورد (طلب المستخدم)
    try:
        info_embed.add_field(
            name="🌐 داش بورد",
            value="[اضغط هنا](https://www.skrew.ct.ws/)",
            inline=False
        )
    except Exception:
        pass

    await interaction.response.send_message(embed=info_embed, ephemeral=True)

@bot.tree.command(name="ping", description="🏓 Check bot latency")
async def ping_command(interaction: discord.Interaction):
    """فحص سرعة استجابة البوت"""
    latency = round(bot.latency * 1000)
    
    if latency < 100:
        color = 0x2ecc71  # أخضر
        status = "Excellent"
        emoji = "🟢"
    elif latency < 200:
        color = 0xf39c12  # أصفر
        status = "Good"
        emoji = "🟡"
    else:
        color = 0xe74c3c  # أحمر
        status = "Poor"
        emoji = "🔴"
    
    ping_embed = discord.Embed(
        title=f"🏓 Pong! {emoji}",
        description=f"**Latency:** {latency}ms\n**Status:** {status}",
        color=color
    )
    
    if is_owner(interaction.user):
        ping_embed.set_footer(text="👑 Owner connection priority")
    
    await interaction.response.send_message(embed=ping_embed, ephemeral=True)

@bot.command(name="status")
async def cmd_set_status(ctx, *, text: str):
    """🟢 تغيير حالة البوت (Owner) — استخدام: !status <النص>"""
    if not is_owner(ctx.author):
        return await ctx.send("❌ هذا الأمر للأونر فقط.", delete_after=5)
    try:
        await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.playing, name=text[:128]))
        await ctx.send("✅ تم تحديث الحالة.", delete_after=10)
    except Exception as e:
        await ctx.send(f"❌ فشل تحديث الحالة: {e}", delete_after=10)

@bot.command(name="setbio")
async def cmd_set_bot_bio(ctx, *, bio: str | None = None):
    """يحاول تحديث وصف حساب التطبيق (About Me). ملاحظة: قد تقيّد ديسكورد تعديل الBio عبر البوت.
    لو الأمر فشل، سنعرض نصاً جاهزاً لتضعه يدوياً في البورتال.
    """
    if not is_owner(ctx.author):
        return await ctx.send("❌ هذا الأمر للأونر فقط.", delete_after=5)

    default_bio = (
        "داش بورد: https://www.skrew.ct.ws/\n"
        "ده بوت سكرو للعبة الورق على ديسكورد — جرب تكتب سكرووو وتبدأ لعب!"
    )
    bio_to_set = bio or default_bio

    # نحاول عبر واجهة Discord HTTP (قد لا يُسمح بذلك دائماً)
    ok = False
    try:
        app = await bot.application_info()
        # توضيح فقط: discord.py لا يوفّر طريقة رسمية لتحديث bio مباشرةً
        # وسينتهي بنا الأمر إلى استخدام واجهة غير مدعومة. لذا نعرض تعليمات.
    except Exception:
        pass

    help_embed = discord.Embed(
        title="📝 إعداد وصف حساب البوت",
        description=(
            "لا تسمح ديسكورد رسمياً بتحديث الـ About Me (Bio) عبر API للبوت.\n"
            "اتّبع الخطوات لتعيين الوصف يدوياً في البورتال:"
        ),
        color=0x3498db,
    )
    help_embed.add_field(
        name="الخطوات",
        value=(
            "1) افتح https://discord.com/developers/applications\n"
            "2) اختر تطبيق البوت الخاص بك\n"
            "3) من تبويب 'General Information' انزل إلى 'Description' أو 'About'\n"
            "4) ضع النص التالي كوصف (Bio):\n\n"
            f"``{bio_to_set}``"
        ),
        inline=False,
    )
    await ctx.send(embed=help_embed)

@bot.command(name="debugowner")
async def cmd_debug_owner(ctx):
    """تشخيص حالة الأونر"""
    debug_embed = discord.Embed(
        title="🔧 Owner Debug Information",
        color=0x3498db
    )
    
    debug_embed.add_field(
        name="👤 User Info",
        value=f"""
        **Name:** {ctx.author.display_name}
        **ID:** {ctx.author.id}
        **Mention:** {ctx.author.mention}
        """,
        inline=True
    )
    
    debug_embed.add_field(
        name="👑 Owner Config",
        value=f"""
        **Base Owners:** {', '.join(str(i) for i in sorted(BASE_OWNER_IDS)) or '—'}
        **Dynamic Owners:** {', '.join(str(i) for i in sorted(DYNAMIC_OWNER_IDS)) or '—'}
        **All Owners Count:** {len(all_owner_ids())}
        **Is Owner:** {is_owner(ctx.author)}
        """,
        inline=True
    )
    
    # معلومات إضافية للمالك فقط
    if is_owner(ctx.author):
        debug_embed.add_field(
            name="✅ Owner Verified",
            value="All systems operational!\nYou have full access.",
            inline=False
        )
        debug_embed.color = 0x2ecc71
    else:
        debug_embed.add_field(
            name="❌ Owner Check Failed",
            value="You are not recognized as owner.\nCheck your ID configuration.",
            inline=False
        )
        debug_embed.color = 0xe74c3c
    
    await ctx.send(embed=debug_embed)

@bot.command(name="claim")
async def cmd_claim_ownership(ctx):
    """المطالبة بملكية البوت"""
    global DYNAMIC_OWNER_IDS

    # إذا لا يوجد أي أونر (أساسي أو ديناميكي) يمكن لأول شخص المطالبة
    if not all_owner_ids():
        DYNAMIC_OWNER_IDS.add(ctx.author.id)
        if save_dynamic_owners(DYNAMIC_OWNER_IDS):
            claim_embed = discord.Embed(
                title="👑 Ownership Claimed!",
                description=f"**{ctx.author.mention} is now the bot owner!** 🎉",
                color=0xFFD700
            )
        else:
            claim_embed = discord.Embed(
                title="❌ Claim Failed",
                description="Failed to save ownership. Try again later.",
                color=0xe74c3c
            )
        return await ctx.send(embed=claim_embed)

    # لو المستخدم بالفعل أونر
    if is_owner(ctx.author):
        claim_embed = discord.Embed(
            title="👑 Already Owner",
            description="You already have owner access.",
            color=0x2ecc71
        )
        return await ctx.send(embed=claim_embed)

    # إذا يوجد أونرز بالفعل، لا يمكن المطالبة تلقائياً
    claim_embed = discord.Embed(
        title="❌ Bot Already Claimed",
        description="Bot already has owners. Ask an owner to add you via !owneradd (by an owner).",
        color=0xe74c3c
    )
    return await ctx.send(embed=claim_embed)

# إدارة الأونرز — تظهر فقط للمشرفين في واجهة السلاش، والتحقق داخل الأمر للأونرز
owners_group = None  # تعطيل مجموعة السلاش الخاصة بالأونرز

@bot.command(name="owneradd")
async def cmd_owners_add(ctx, member: discord.Member):
    if not is_owner(ctx.author):
        return await ctx.send("❌ هذا الأمر للأونرز فقط.", delete_after=5)
    global DYNAMIC_OWNER_IDS
    if member.id in all_owner_ids():
        return await ctx.send("ℹ️ هذا العضو أونر بالفعل.", delete_after=10)
    DYNAMIC_OWNER_IDS.add(int(member.id))
    if save_dynamic_owners(DYNAMIC_OWNER_IDS):
        await ctx.send(f"✅ تمت إضافة {member.mention} لقائمة الأونرز.", delete_after=10)
    else:
        await ctx.send("❌ فشل حفظ التغييرات.", delete_after=10)

@bot.command(name="ownerremove")
async def cmd_owners_remove(ctx, member: discord.Member):
    if not is_owner(ctx.author):
        return await ctx.send("❌ هذا الأمر للأونرز فقط.", delete_after=5)
    global DYNAMIC_OWNER_IDS
    if member.id in BASE_OWNER_IDS:
        return await ctx.send("❌ لا يمكن إزالة أونر أساسي من داخل البوت.", delete_after=10)
    if member.id not in DYNAMIC_OWNER_IDS:
        return await ctx.send("ℹ️ هذا العضو ليس في قائمة الأونرز الديناميكيين.", delete_after=10)
    DYNAMIC_OWNER_IDS.discard(int(member.id))
    if save_dynamic_owners(DYNAMIC_OWNER_IDS):
        await ctx.send(f"✅ تمت إزالة {member.mention} من الأونرز.", delete_after=10)
    else:
        await ctx.send("❌ فشل حفظ التغييرات.", delete_after=10)

@bot.command(name="owners")
async def cmd_owners_list(ctx):
    ids = sorted(all_owner_ids())
    lines = []
    for oid in ids:
        user = ctx.guild.get_member(oid) if ctx.guild else None
        name = user.mention if user else f"<@{oid}>"
        base = " (base)" if oid in BASE_OWNER_IDS else ""
        lines.append(f"• {name}{base}")
    embed = discord.Embed(title="👑 Owners", description="\n".join(lines) or "—", color=0xFFD700)
    await ctx.send(embed=embed)

@bot.command(name="resync")
async def cmd_resync_commands(ctx):
    """إعادة مزامنة أوامر السلاش يدوياً"""
    if not is_owner(ctx.author):
        return await ctx.send("❌ هذا الأمر حصري للأونر فقط! 👑", delete_after=5)
    
    try:
        synced = await bot.tree.sync()
        msg = f"✅ تمت مزامنة {len(synced)} أمر عالمياً"
        guild = ctx.guild
        if guild:
            bot.tree.copy_global_to(guild=guild)
            gsynced = await bot.tree.sync(guild=guild)
            msg += f"\n⚡ مزامنة فورية للسيرفر: {len(gsynced)} أمر"
        embed = discord.Embed(title="🔄 تمت إعادة المزامنة", description=msg, color=0x2ecc71)
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ خطأ في المزامنة",
            description=f"فشلت إعادة المزامنة: {str(e)}",
            color=0xe74c3c
        )
        await ctx.send(embed=error_embed)

@bot.command(name="slashdebug")
async def cmd_slash_debug(ctx):
    """تشخيص مشاكل أوامر السلاش"""
    embed = discord.Embed(
        title="🔧 تشخيص أوامر السلاش",
        color=0x3498db
    )
    
    # معلومات البوت
    embed.add_field(
        name="🤖 معلومات البوت",
    value=f"**الاسم:** {bot.user.name}\n**ID:** {bot.user.id}\n**صلاحيات:** {'مدير' if ctx.guild and ctx.guild.me.guild_permissions.administrator else 'محدودة'}",
        inline=True
    )
    
    # إحصائيات الأوامر
    commands_count = len(bot.tree.get_commands())
    embed.add_field(
        name="📊 الأوامر المسجلة",
        value=f"**العدد:** {commands_count}\n**آخر مزامنة:** عند التشغيل",
        inline=True
    )
    
    # حلول المشاكل الشائعة
    embed.add_field(
        name="🛠️ حلول سريعة",
        value="• استخدم `/resync` لإعادة المزامنة\n• تأكد من صلاحيات البوت\n• انتظر 5 دقائق بعد إضافة البوت",
        inline=False
    )
    
    # معلومات للأونر فقط
    if is_owner(ctx.author):
        embed.add_field(
            name="👑 معلومات الأونر",
            value=f"**مزامنة السيرفر:** {'مفعلة' if DEV_GUILD_ID else 'معطلة'}\n**Guild ID:** {ctx.guild.id if ctx.guild else 'غير متوفر'}",
            inline=False
        )
        embed.set_footer(text="👑 أنت مالك البوت - يمكنك استخدام /resync")
    
    await ctx.send(embed=embed)

# أوامر اللعبة الرئيسية
@bot.tree.command(name="screw", description="🎴 Start a new Screw card game")
async def slash_start(interaction: discord.Interaction):
    if interaction.channel.id in active_lobbies:
        embed = discord.Embed(
            title="🎯 Game Already Active",
            description="**There's already an active game in this channel!**\n\nWait for it to finish or use `/end` to stop it (Admin only).",
            color=0xe74c3c
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    lobby = Lobby(interaction.channel)
    active_lobbies[interaction.channel.id] = lobby
    dummy_holder = {}
    view = JoinView(lobby, dummy_holder)
    embed = generate_lobby_embed(lobby, countdown=20)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
    msg = await interaction.original_response()
    dummy_holder['msg'] = msg
    lobby.join_view = view
    lobby.join_msg = msg

    for i in range(20, 0, -1):
        await asyncio.sleep(1)
        if lobby.is_stopped:
            break
        try:
            await msg.edit(embed=generate_lobby_embed(lobby, countdown=i), view=view)
        except Exception:
            pass
    try:
        view.stop()
        final_embed = discord.Embed(title="⏰ انتهى وقت الانضمام", description="**انتهى وقت الانضمام للعبة**", color=0xf39c12)
        await msg.edit(embed=final_embed, view=None)
    except Exception:
        pass

    if len(lobby.players) < 2:
        error_embed = discord.Embed(title="❌ عدد غير كافي", description="يحتاج على الأقل 2 لاعبين لبدء اللعبة!", color=0xe74c3c)
        await interaction.followup.send(embed=error_embed, ephemeral=True)
        try:
            del active_lobbies[interaction.channel.id]
        except KeyError:
            pass
        return

    lobby.deck = create_full_deck()
    deal_hands(lobby)
    await start_round(interaction.channel, lobby)

@bot.tree.command(name="stats", description="📊 View player stats and points")
@app_commands.describe(member="Target member (optional)")
async def slash_points(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    target = member or interaction.user
    guild_id = interaction.guild.id if interaction.guild else 0
    stats = points_manager.get_user_stats(guild_id, target.id)
    await interaction.response.send_message(embed=_build_points_embed(target, stats), ephemeral=True)

@bot.tree.command(name="شراء", description="🛒 شراء مود صاحب صحبه (50 نقطة)")
async def buy_teams_mode(interaction: discord.Interaction):
    """شراء مود صاحب صحبه بـ 50 نقطة"""
    guild_id = interaction.guild.id if interaction.guild else 0
    user_id = interaction.user.id
    
    # التحقق من الشراء السابق
    if has_purchased(guild_id, user_id, "teams_mode"):
        already_embed = discord.Embed(
            title="✅ تملك المود بالفعل",
            description="**أنت تمتلك مود صاحب صحبه بالفعل!**\n\nيمكنك استخدام الأمر: `سكرووو صاحب صحبه`",
            color=0x2ecc71
        )
        already_embed.set_footer(text="استمتع باللعب!")
        return await interaction.response.send_message(embed=already_embed, ephemeral=True)
    
    # التحقق من النقاط
    stats = points_manager.get_user_stats(guild_id, user_id)
    current_points = int(stats.get("points", 0))
    price = 50
    
    if current_points < price:
        insufficient_embed = discord.Embed(
            title="❌ نقاط غير كافية",
            description=f"**تحتاج {price} نقطة لشراء مود صاحب صحبه!**",
            color=0xe74c3c
        )
        insufficient_embed.add_field(
            name="💰 نقاطك الحالية",
            value=f"{current_points} نقطة",
            inline=True
        )
        insufficient_embed.add_field(
            name="📉 النقص",
            value=f"{price - current_points} نقطة",
            inline=True
        )
        insufficient_embed.set_footer(text="العب المزيد من الألعاب لكسب نقاط!")
        return await interaction.response.send_message(embed=insufficient_embed, ephemeral=True)
    
    # واجهة التأكيد
    class ConfirmPurchaseView(discord.ui.View):
        def __init__(self, timeout=30):
            super().__init__(timeout=timeout)
            
        @discord.ui.button(label="✅ تأكيد الشراء", style=discord.ButtonStyle.success)
        async def confirm(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
            if btn_interaction.user != interaction.user:
                return await btn_interaction.response.send_message("❌ ليس من حقك!", ephemeral=True)
            
            # خصم النقاط
            points_manager.add_points(guild_id, user_id, -price)
            
            # إضافة المشترى
            add_purchase(guild_id, user_id, "teams_mode")
            
            # رسالة النجاح
            success_embed = discord.Embed(
                title="🎉 تمت عملية الشراء بنجاح!",
                description="**مبروك! تم شراء مود صاحب صحبه بنجاح!**",
                color=0x00ff00
            )
            success_embed.add_field(
                name="💳 التفاصيل",
                value=f"• **المود:** صاحب صحبه (Teams Mode)\n• **السعر:** {price} نقطة\n• **النقاط المتبقية:** {current_points - price} نقطة",
                inline=False
            )
            success_embed.add_field(
                name="🎮 كيفية الاستخدام",
                value="اكتب في أي قناة: `سكرووو صاحب صحبه`",
                inline=False
            )
            success_embed.set_footer(text="استمتع باللعب مع أصدقائك!")
            
            # تعطيل الأزرار
            for child in self.children:
                child.disabled = True
            
            await btn_interaction.response.edit_message(embed=success_embed, view=self)
            
            # إشعار عام
            await interaction.channel.send(f"🎊 **{interaction.user.mention}** اشترى مود صاحب صحبه! تهانينا! 🎉")
            
            self.stop()
        
        @discord.ui.button(label="❌ إلغاء", style=discord.ButtonStyle.danger)
        async def cancel(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
            if btn_interaction.user != interaction.user:
                return await btn_interaction.response.send_message("❌ ليس من حقك!", ephemeral=True)
            
            cancel_embed = discord.Embed(
                title="❌ تم الإلغاء",
                description="تم إلغاء عملية الشراء",
                color=0x95a5a6
            )
            
            for child in self.children:
                child.disabled = True
            
            await btn_interaction.response.edit_message(embed=cancel_embed, view=self)
            self.stop()
    
    # عرض واجهة التأكيد
    confirm_embed = discord.Embed(
        title="🛒 تأكيد الشراء",
        description="**هل أنت متأكد من شراء مود صاحب صحبه?**",
        color=0xf39c12
    )
    confirm_embed.add_field(
        name="📦 المنتج",
        value="مود صاحب صحبه (Teams Mode)",
        inline=True
    )
    confirm_embed.add_field(
        name="💰 السعر",
        value=f"{price} نقطة",
        inline=True
    )
    confirm_embed.add_field(
        name="💳 نقاطك الحالية",
        value=f"{current_points} نقطة",
        inline=True
    )
    confirm_embed.add_field(
        name="📊 بعد الشراء",
        value=f"{current_points - price} نقطة",
        inline=True
    )
    confirm_embed.add_field(
        name="✨ المميزات",
        value="• لعب جماعي مع الأصدقاء\n• تقسيم تلقائي للفرق\n• بطاقات خاصة جديدة",
        inline=False
    )
    confirm_embed.set_footer(text="لديك 30 ثانية للتأكيد")
    
    view = ConfirmPurchaseView()
    await interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=True)

@bot.command(name="end")
async def cmd_end(ctx):
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(title="❌ صلاحية مرفوضة", description="هذا الأمر متاح فقط للمشرفين.", color=0xe74c3c)
        return await ctx.send(embed=embed, delete_after=5)
    if ctx.channel.id not in active_lobbies:
        embed = discord.Embed(title="❌ لا توجد لعبة نشطة", description="لا توجد لعبة نشطة في هذه القناة لإيقافها", color=0xe74c3c)
        return await ctx.send(embed=embed, delete_after=5)
    # استدعاء نفس منطق أمر !وقف
    ctx_channel = ctx.channel
    lobby = active_lobbies[ctx_channel.id]
    lobby.is_stopped = True
    try:
        if lobby.join_view:
            for child in lobby.join_view.children:
                child.disabled = True
            lobby.join_view.stop()
            if lobby.join_msg:
                await lobby.join_msg.edit(view=lobby.join_view)
    except Exception:
        pass
    try:
        if lobby.current_draw_view:
            for child in lobby.current_draw_view.children:
                child.disabled = True
            lobby.current_draw_view.stop()
            if lobby.current_draw_msg:
                await lobby.current_draw_msg.edit(view=lobby.current_draw_view)
    except Exception:
        pass
    del active_lobbies[ctx_channel.id]
    stop_embed = discord.Embed(
        title="🛑 تم إيقاف اللعبة",
        description=f"**تم إيقاف اللعبة بواسطة {ctx.author.mention}**",
        color=0xe74c3c
    )
    if lobby.players:
        players_list = "\n".join([f"• {format_member(p)}" for p in lobby.players])
        stop_embed.add_field(name="👥 اللاعبين المشاركين", value=players_list, inline=False)
    stop_embed.add_field(name="📊 إحصائيات اللعبة", value=f"• عدد الجولات: {lobby.round_number}\n• عدد اللاعبين: {len(lobby.players)}", inline=True)
    stop_embed.add_field(name="🎮 بدء لعبة جديدة", value="يمكن بدء لعبة جديدة بكتابة سكرووو أو /start", inline=True)
    await ctx.send(embed=stop_embed)

@bot.command(name="kick")
async def cmd_kick(ctx, player: discord.Member):
    """طرد لاعب من اللعبة الحالية"""
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="❌ صلاحية مرفوضة", 
            description="هذا الأمر متاح فقط للمشرفين.",
            color=0xe74c3c
        )
        return await ctx.send(embed=embed, delete_after=5)
    
    if ctx.channel.id not in active_lobbies:
        embed = discord.Embed(
            title="❌ لا توجد لعبة نشطة",
            description="لا توجد لعبة نشطة في هذه القناة!",
            color=0xe74c3c
        )
        return await ctx.send(embed=embed, delete_after=5)
    
    lobby = active_lobbies[ctx.channel.id]
    
    # التحقق من وجود اللاعب في اللعبة
    if player not in lobby.players:
        embed = discord.Embed(
            title="❌ اللاعب غير موجود",
            description=f"**{player.display_name}** ليس في اللعبة الحالية!",
            color=0xe74c3c
        )
        return await ctx.send(embed=embed, delete_after=5)
    
    # طرد اللاعب
    lobby.players.remove(player)
    
    # إزالة أوراقه
    if player in lobby.hands:
        lobby.hands.pop(player)
    
    kick_embed = discord.Embed(
        title="🦵 تم طرد لاعب",
        description=f"**{format_member(player)}** تم طرده من اللعبة بواسطة {ctx.author.mention}",
        color=0xf39c12
    )
    kick_embed.add_field(
        name="👥 اللاعبين المتبقين",
        value=f"{len(lobby.players)} لاعب",
        inline=True
    )
    
    await ctx.send(embed=kick_embed)
    
    # فحص إذا بقى لاعب واحد فقط - إقفال اللعبة
    if len(lobby.players) <= 1:
        end_embed = discord.Embed(
            title="🛑 إنهاء اللعبة تلقائياً",
            description="**تم إنهاء اللعبة لعدم وجود لاعبين كافيين!**\n\nيحتاج على الأقل لاعبين 2 للعب.",
            color=0xe74c3c
        )
        if lobby.players:
            end_embed.add_field(
                name="👤 اللاعب المتبقي",
                value=format_member(lobby.players[0]),
                inline=False
            )
            end_embed.add_field(
                name="🏆 النتيجة",
                value=f"**{lobby.players[0].display_name}** فاز بشكل افتراضي!",
                inline=False
            )
        await ctx.channel.send(embed=end_embed)
        
        # تنظيف اللوبي وإزالته
        lobby.cleanup_lobby()
        active_lobbies.pop(ctx.channel.id, None)

@bot.command(name="شرح_اللعبة")
async def game_explanation(ctx):
    """شرح مفصل لقواعد لعبة سكرو مع واجهة تفاعلية"""
    
    # إنشاء صفحات الشرح
    pages = []
    
    # الصفحة 1: المقدمة والهدف
    page1 = discord.Embed(
        title="🎴 شرح لعبة سكرو - الصفحة 1/5",
        description="**مرحباً بك في لعبة سكرو! 🎮**\n\nلعبة الورق الاستراتيجية المليئة بالتحديات والمفاجآت",
        color=0x9b59b6
    )
    page1.add_field(
        name="🎯 الهدف الأساسي",
        value="""• **الهدف**: الحصول على أقل عدد ممكن من النقاط في نهاية اللعبة
• كل ورقة لها قيمة نقاط محددة
• الفائز هو من لديه أقل مجموع نقاط
• استخدم البطاقات الخاصة بذكاء للفوز""",
        inline=False
    )
    page1.add_field(
        name="📋 معلومات سريعة",
        value="""• عدد اللاعبين: 2-8 لاعبين
• كل لاعب يبدأ بـ 4 أوراق
• يمكنك مشاهدة ورقتين فقط في البداية
• مدة الجولة: 20 ثانية للانضمام""",
        inline=False
    )
    page1.set_thumbnail(url="https://cdn.discordapp.com/attachments/1303340209575825449/1425772990091755581/Untitled_design_1.png")
    
    # الصفحة 2: طريقة اللعب
    page2 = discord.Embed(
        title="🔄 طريقة اللعب - الصفحة 2/5",
        color=0x3498db
    )
    page2.add_field(
        name="🚀 بداية اللعبة",
        value="""1. اكتب `سكرووو` لبدء اللعبة
2. انضم للغرفة خلال 20 ثانية
3. شاهد ورقتين من أصل 4 أوراق
4. ابدأ الأدوار بشكل عشوائي""",
        inline=False
    )
    page2.add_field(
        name="🎯 خلال دورك",
        value="""• **اسحب ورقة**: من الديك الرئيسي
• **خذ من الأرض**: استبدل ورقة من يدك
• **تبصر**: قارن ورقتك مع الأرض
• **سكرو**: أعلن نهاية اللعبة""",
        inline=False
    )
    page2.add_field(
        name="⏰ توقيت مهم",
        value="• 30 ثانية لكل دور\n• 20 ثانية لاتخاذ القرارات\n• خطط استراتيجيتك مسبقاً",
        inline=False
    )
    
    # الصفحة 3: البطاقات الأساسية
    page3 = discord.Embed(
        title="🃏 البطاقات الأساسية - الصفحة 3/5",
        color=0xe74c3c
    )
    page3.add_field(
        name="🔢 البطاقات الرقمية",
        value="""• **1-6**: قيمتها الرقم المكتوب (1-6 نقطة)
• **7, 8**: انظر إلى أوراقك 👀
• **9, 10**: انظر إلى أوراق الخصوم 🔍
• **-1**: تخسر نقطة واحدة ❌""",
        inline=False
    )
    page3.add_field(
        name="🎭 البطاقات الخاصة",
        value="""• **خد بس**: أعط ورقة لخصم 🎁
• **خد وهات**: بدل ورقة مع خصم 🔄
• **see swap**: انظر وقرر 🔎
• **بصرة**: تخلص من ورقة 🎯""",
        inline=False
    )
    
    # الصفحة 4: بطاقات السكرو والمخاطر
    page4 = discord.Embed(
        title="⚡ بطاقات المخاطر - الصفحة 4/5",
        color=0xf39c12
    )
    page4.add_field(
        name="🚨 بطاقات السكرو",
        value="""• **سكرو أخضر**: آمن (0 نقطة) 💚
• **سكرو أحمر**: خطير (25 نقطة) 🔴
• **+20**: تضيف 20 نقطة 📈
• أعلن سكرو عندما تشعر بالثقة!""",
        inline=False
    )
    page4.add_field(
        name="🎪 البطاقات الخاصة",
        value="""• **كعب داير**: خيارات متعددة 🎪
• **الحرامي**: مغامرة محفوفة بالمخاطر 🦹
• يمكن أن تغير هذه البطاقات مجرى اللعبة""",
        inline=False
    )
    
    # الصفحة 5: الاستراتيجيات والنقاط
    page5 = discord.Embed(
        title="🏆 الاستراتيجيات والفوز - الصفحة 5/5",
        color=0x2ecc71
    )
    page5.add_field(
        name="💡 استراتيجيات الفوز",
        value="""• تخلص من البطاقات عالية القيمة أولاً
• استخدم البطاقات الخاصة في الوقت المناسب
• راقب أوراق المنافسين
• أعلن 'سكرو' عندما تكون مستعداً""",
        inline=False
    )
    page5.add_field(
        name="🏅 نظام النقاط",
        value="""• **الأقل نقاطاً يفوز** 🥇
• إذا تساوى لاعبين: الأقل أوراقاً يفوز
• إذا تساوى لاعبين تماماً: تعادل 🤝
• الحرامي: قد يغير النتائج""",
        inline=False
    )
    page5.add_field(
        name="🎊 نصائح أخيرة",
        value="""• خطط لاستراتيجيتك من البداية
• تذكر أنك لا ترى كل أوراقك
• استخدم خاصية التبصر بحكمة
• استمتع باللعبة! 🎉""",
        inline=False
    )
    
    pages = [page1, page2, page3, page4, page5]
    
    # إنشاء واجهة التنقل
    class ExplanationView(discord.ui.View):
        def __init__(self, pages, timeout=120):
            super().__init__(timeout=timeout)
            self.pages = pages
            self.current_page = 0
            self.message = None
            
        async def update_embed(self, interaction: discord.Interaction):
            # تحديث حالة الأزرار
            self.previous_button.disabled = (self.current_page == 0)
            self.next_button.disabled = (self.current_page == len(self.pages) - 1)
            self.page_info.label = f"الصفحة {self.current_page + 1}/{len(self.pages)}"
            
            # إرسال التحديث
            await interaction.response.edit_message(
                embed=self.pages[self.current_page],
                view=self
            )
        
        @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.primary, disabled=True)
        async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.current_page -= 1
            await self.update_embed(interaction)
        
        @discord.ui.button(style=discord.ButtonStyle.secondary, disabled=True)
        async def page_info(self, interaction: discord.Interaction, button: discord.ui.Button):
            # زر المعلومات لا يفعل شيء عند الضغط
            await interaction.response.defer()
        
        @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.primary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.current_page += 1
            await self.update_embed(interaction)
        
        @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger)
        async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            # تعطيل جميع الأزرار عند الإيقاف
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            self.stop()
        
        async def on_timeout(self):
            # تعطيل الأزرار عند انتهاء الوقت
            for child in self.children:
                child.disabled = True
            if self.message:
                try:
                    await self.message.edit(view=self)
                except:
                    pass
    
    # إرسال الرسالة مع الواجهة
    view = ExplanationView(pages)
    view.message = await ctx.send(embed=pages[0], view=view)

# نسخة بديلة مع أزرار أكثر تفاعلية (اختيارية)
@bot.command(name="شرح")
async def short_explanation(ctx):
    """شرح سريع للعبة مع أزرار اختيار المواضيع"""
    
    main_embed = discord.Embed(
        title="🎴 دليل لعبة سكرو السريع",
        description="**اختر الموضوع الذي تريد معرفة المزيد عنه:**\n\nاستخدم الأزرار أدناه للانتقال إلى الشرح المفصل",
        color=0x9b59b6
    )
    
    class TopicView(discord.ui.View):
        def __init__(self, timeout=60):
            super().__init__(timeout=timeout)
        
        @discord.ui.button(label="🎯 الهدف الأساسي", style=discord.ButtonStyle.primary)
        async def goal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="🎯 الهدف الأساسي",
                description="**هدفك في اللعبة هو الحصول على أقل عدد ممكن من النقاط**",
                color=0x2ecc71
            )
            embed.add_field(
                name="كيف تفوز؟",
                value="""• كل ورقة لها قيمة نقاط
• اجمع أقل نقاط ممكنة
• استخدم البطاقات الخاصة بذكاء
• أعلن سكرو في الوقت المناسب""",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        @discord.ui.button(label="🔄 طريقة اللعب", style=discord.ButtonStyle.primary)
        async def gameplay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="🔄 طريقة اللعب",
                description="**خطوات اللعبة من البداية للنهاية**",
                color=0x3498db
            )
            embed.add_field(
                name="الدور النموذجي",
                value="""1. اسحب ورقة جديدة
2. اختر: احتفظ أو ارمي
3. استخدم البطاقات الخاصة
4. انتقل للاعب التالي""",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        @discord.ui.button(label="🃏 البطاقات", style=discord.ButtonStyle.primary)
        async def cards_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="🃏 أنواع البطاقات",
                description="**تعرف على البطاقات المختلفة وتأثيراتها**",
                color=0xe74c3c
            )
            embed.add_field(
                name="البطاقات الأساسية",
                value="• الأرقام (1-10)\n• -1 نقطة\n• سكرو أخضر/أحمر",
                inline=True
            )
            embed.add_field(
                name="البطاقات الخاصة",
                value="• خد بس/وهات\n• كعب داير\n• بصرة\n• الحرامي",
                inline=True
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        @discord.ui.button(label="💡 استراتيجيات", style=discord.ButtonStyle.success)
        async def strategies_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="💡 نصائح استراتيجية",
                description="**استراتيجيات لزيادة فرصك في الفوز**",
                color=0xf39c12
            )
            embed.add_field(
                name="نصائح مهمة",
                value="""• تخلص من البطاقات عالية القيمة
• استخدم التبصر بحكمة
• راقب منافسيك
• لا تنتظر كثيراً للإعلان""",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        @discord.ui.button(label="📖 الشرح الكامل", style=discord.ButtonStyle.secondary)
        async def full_explanation_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="مش هشرح تاني انا لا",
                color=0xf39c12
            )
            embed.add_field(
                name="شرح ام اللعبة",
                value="""متتنيل تلعب وانت ساكت انت هتقرفنا""",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
    main_embed.set_footer(text="اختر أي موضوع للاطلاع على التفاصيل | انتهاء الوقت: 60 ثانية")
    await ctx.send(embed=main_embed, view=TopicView())
    
@bot.command(name="وقف")
async def stop_game(ctx):
    """إيقاف اللعبة الحالية (للمشرفين فقط)"""
    
    # التحقق من صلاحيات المشرف
    if not ctx.author.guild_permissions.administrator:
        no_permission_embed = discord.Embed(
            title="❌ صلاحية مرفوضة",
            description="**ليس لديك صلاحية إيقاف اللعبة!**\n\nهذا الأمر متاح فقط للمشرفين.",
            color=0xe74c3c
        )
        return await ctx.send(embed=no_permission_embed, delete_after=5)
    
    if ctx.channel.id not in active_lobbies:
        error_embed = discord.Embed(
            title="❌ لا توجد لعبة نشطة",
            description="لا توجد لعبة نشطة في هذه القناة لإيقافها",
            color=0xe74c3c
        )
        return await ctx.send(embed=error_embed, delete_after=5)
    
    lobby = active_lobbies[ctx.channel.id]
    
    # وضع علامة إيقاف للعبة
    lobby.is_stopped = True
    
    # إيقاف أي واجهات/تايمرز نشطة
    try:
        if lobby.join_view:
            for child in lobby.join_view.children:
                child.disabled = True
            lobby.join_view.stop()
            if lobby.join_msg:
                await lobby.join_msg.edit(view=lobby.join_view)
    except Exception:
        pass
    try:
        if lobby.current_draw_view:
            for child in lobby.current_draw_view.children:
                child.disabled = True
            lobby.current_draw_view.stop()
            if lobby.current_draw_msg:
                await lobby.current_draw_msg.edit(view=lobby.current_draw_view)
    except Exception:
        pass

    # إلغاء اللعبة من القائمة النشطة
    del active_lobbies[ctx.channel.id]
    
    stop_embed = discord.Embed(
        title="🛑 تم إيقاف اللعبة",
        description=f"**تم إيقاف اللعبة بواسطة {ctx.author.mention}**",
        color=0xe74c3c
    )
    
    if lobby.players:
        players_list = "\n".join([f"• {format_member(p)}" for p in lobby.players])
        stop_embed.add_field(
            name="👥 اللاعبين المشاركين",
            value=players_list,
            inline=False
        )
    
    stop_embed.add_field(
        name="📊 إحصائيات اللعبة",
        value=f"• عدد الجولات: {lobby.round_number}\n• عدد اللاعبين: {len(lobby.players)}",
        inline=True
    )
    
    stop_embed.add_field(
        name="🎮 بدء لعبة جديدة",
        value="يمكن بدء لعبة جديدة بكتابة `سكرووو`",
        inline=True
    )
    
    stop_embed.set_footer(text="تم الإيقاف بواسطة المشرف")
    await ctx.send(embed=stop_embed)

# -----------------------------
# لوحة تحكم الأونر (Owner Control Panel)
# -----------------------------
class OwnerControlView(discord.ui.View):
    """لوحة تحكم خاصة بالأونر مع أزرار للتحكم في الألعاب"""
    
    def __init__(self, timeout=120):
        super().__init__(timeout=timeout)
        
    @discord.ui.button(label="🚀 بدء فوري", style=discord.ButtonStyle.success, emoji="⚡")
    async def instant_start(self, interaction: discord.Interaction, button: discord.ui.Button):
        """بدء اللعبة فوراً بدون انتظار"""
        if interaction.channel.id in active_lobbies:
            lobby = active_lobbies[interaction.channel.id]
            if len(lobby.players) >= 2:
                # إيقاف العد التنازلي وبدء اللعبة فوراً
                lobby.is_stopped = False
                try:
                    if lobby.join_view:
                        lobby.join_view.stop()
                except:
                    pass
                
                lobby.deck = create_full_deck()
                deal_hands(lobby)
                await interaction.response.send_message("👑 **الأونر أمر ببدء فوري!** ⚡", ephemeral=True)
                await start_round(interaction.channel, lobby)
            else:
                await interaction.response.send_message("❌ يحتاج على الأقل 2 لاعبين للبدء!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ لا توجد لعبة نشطة في هذه القناة!", ephemeral=True)
    
    @discord.ui.button(label="⏰ تمديد الوقت", style=discord.ButtonStyle.primary, emoji="➕")
    async def extend_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        """تمديد وقت الانضمام"""
        await interaction.response.send_message("👑 **تم تمديد وقت الانضمام +10 ثواني بأمر الأونر!**", ephemeral=False)
        # هنا يمكن إضافة منطق تمديد الوقت الفعلي
        
    @discord.ui.button(label="🦵 طرد AFK", style=discord.ButtonStyle.danger, emoji="👢")
    async def kick_afk(self, interaction: discord.Interaction, button: discord.ui.Button):
        """إزالة اللاعبين غير النشطين"""
        if interaction.channel.id in active_lobbies:
            lobby = active_lobbies[interaction.channel.id]
            # منطق بسيط لطرد آخر لاعب انضم (مثال)
            if lobby.players:
                removed_player = lobby.players.pop()
                await interaction.response.send_message(f"👑 **الأونر طرد {removed_player.mention} لعدم النشاط!**", ephemeral=False)
                
                # فحص إذا بقى لاعب واحد فقط - إقفال اللعبة
                if len(lobby.players) <= 1:
                    end_embed = discord.Embed(
                        title="🛑 إنهاء اللعبة تلقائياً",
                        description="**تم إنهاء اللعبة لعدم وجود لاعبين كافيين!**\n\nيحتاج على الأقل لاعبين 2 للعب.",
                        color=0xe74c3c
                    )
                    if lobby.players:
                        end_embed.add_field(
                            name="👤 اللاعب المتبقي",
                            value=format_member(lobby.players[0]),
                            inline=False
                        )
                    await interaction.channel.send(embed=end_embed)
                    
                    # تنظيف اللوبي وإزالته
                    lobby.cleanup_lobby()
                    active_lobbies.pop(interaction.channel.id, None)
            else:
                await interaction.response.send_message("❌ لا يوجد لاعبين لطردهم!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ لا توجد لعبة نشطة!", ephemeral=True)
    
    @discord.ui.button(label="🔒 قفل القناة", style=discord.ButtonStyle.secondary, emoji="🚫")
    async def lock_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """منع الألعاب الجديدة مؤقتاً"""
        # يمكن إضافة نظام قفل للقناة هنا
        await interaction.response.send_message("👑 **تم قفل القناة مؤقتاً بأمر الأونر!** 🔒\n*الألعاب الجديدة معطلة.*", ephemeral=False)
        
    @discord.ui.button(label="📊 إحصائيات سريعة", style=discord.ButtonStyle.secondary, emoji="📈")
    async def quick_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """عرض إحصائيات سريعة للسيرفر"""
        guild_id = interaction.guild.id if interaction.guild else 0
        # حساب إحصائيات بسيطة
        active_games = len(active_lobbies)
        
        stats_embed = discord.Embed(
            title="📊 إحصائيات السيرفر - لوحة الأونر",
            color=0xFFD700  # ذهبي للأونر
        )
        stats_embed.add_field(name="🎮 ألعاب نشطة", value=f"{active_games}", inline=True)
        stats_embed.add_field(name="🏆 إجمالي المسجلين", value="قريباً", inline=True)
        stats_embed.add_field(name="📈 متوسط الألعاب يومياً", value="قريباً", inline=True)
        stats_embed.set_footer(text="👑 لوحة الأونر الخاصة")
        
        await interaction.response.send_message(embed=stats_embed, ephemeral=True)

@bot.command(name="control")
async def cmd_owner_panel(ctx):
    """لوحة تحكم حصرية للأونر"""
    if not is_owner(ctx.author):
        embed = discord.Embed(
            title="❌ صلاحية محظورة",
            description="**هذه اللوحة حصرية للأونر فقط!** 👑",
            color=0xe74c3c
        )
        return await ctx.send(embed=embed)
    
    panel_embed = discord.Embed(
        title="👑 لوحة تحكم الأونر",
        description="**أهلاً بك يا ملك السيرفر!** ✨\n\nاستخدم الأزرار أدناه للتحكم الكامل في الألعاب:",
        color=0xFFD700  # ذهبي
    )
    panel_embed.add_field(
        name="🚀 التحكم في الألعاب",
        value="• بدء فوري بدون انتظار\n• تمديد وقت الانضمام\n• طرد اللاعبين غير النشطين",
        inline=True
    )
    panel_embed.add_field(
        name="🔧 إدارة السيرفر", 
        value="• قفل/فتح القنوات\n• إحصائيات مفصلة\n• مراقبة الأنشطة",
        inline=True
    )
    panel_embed.set_footer(text="👑 صلاحيات الأونر • مدة اللوحة: 120 ثانية")
    
    view = OwnerControlView()
    await ctx.send(embed=panel_embed, view=view)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        error_embed = discord.Embed(
            title="❌ صلاحية مرفوضة",
            description="ليس لديك الصلاحية الكافية لاستخدام هذا الأمر!",
            color=0xe74c3c
        )
        await ctx.send(embed=error_embed, ephemeral=True)
    else:
        # يمكنك إضافة معالجة لأخطاء أخرى هنا
        pass

# -----------------------------
# نظام البطاقات والصور
# -----------------------------
CARD_IMAGES = {
    "-1": "https://cdn.discordapp.com/attachments/1423980365898580116/1425206354649419879/Untitled_design.png?ex=68e6be5a&is=68e56cda&hm=79e6dd00f14c59512180aa311388257f30ca4bfb2900b97ee1702522ee06ece0",
    "سكرو أخضر": "https://cdn.discordapp.com/attachments/1424354249302609995/1425206984822493275/Untitled_design_18.png?ex=68e6bef0&is=68e56d70&hm=7cf051932856c023215f8ece0bebc5f090f58f8ca1f61a037d50412a1b0d054a",
    "1": "https://cdn.discordapp.com/attachments/1423980365898580116/1425202683622588629/1.png?ex=68e6baee&is=68e5696e&hm=f18a78c12612eb692f128fcfe5cdb9cd74cb97f1d515a98c38a14e74c34d874d",
    "2": "https://cdn.discordapp.com/attachments/1423980365898580116/1425206404771348562/Untitled_design_2.png?ex=68e6be65&is=68e56ce5&hm=5b48b55d36df763ab53d4138b3a384e8a8b378198af9d5e2bd4e82cfe508f6b8",
    "3": "https://cdn.discordapp.com/attachments/1423980365898580116/1425206570572185710/Untitled_design_3.png?ex=68e6be8d&is=68e56d0d&hm=d1533c9d8b6215719679f20cb5182f22c8571fea57b127365da3d09703def47c",
    "4": "https://cdn.discordapp.com/attachments/1424354249302609995/1425206663358447677/Untitled_design_4.png?ex=68e6bea3&is=68e56d23&hm=0a43b20b7acfc17d9f0264c1714172f9ea69f0a8382f4519beae5509e9c74e35",
    "5": "https://cdn.discordapp.com/attachments/1424354249302609995/1425206697491828828/Untitled_design_5.png?ex=68e6beab&is=68e56d2b&hm=3184b0a38c62c066dba2b96279b80f2cf0cd0b11ddabb227ccc72bda2439e32d",
    "6": "https://cdn.discordapp.com/attachments/1424354249302609995/1425413144460660776/6.png?ex=68e77ef0&is=68e62d70&hm=9558dad19c47c32abc2e9340da7a1466ef649e0d52d88098ee69a1835d3e9f05",
    "7": "https://cdn.discordapp.com/attachments/1424354249302609995/1425206741716570222/Untitled_design_7.png?ex=68e6beb6&is=68e56d36&hm=db3405151ab5e1cee806ed78fb361c152e833444d58884e2f1742e3574b817da",
    "8": "https://cdn.discordapp.com/attachments/1424354249302609995/1425206763980062884/Untitled_design_8.png?ex=68e6bebb&is=68e56d3b&hm=f34d9593f6b7cbc1674f541fdbd8fb59b6dad7b0786152130705b10e2cd52526",
    "9": "https://cdn.discordapp.com/attachments/1424354249302609995/1425208413230596156/9.png?ex=68e6c044&is=68e56ec4&hm=a6b0e48f59c34b2e1c96a262f4350cc77b8ecd98653d7b03f39dd2ec2bfb3691",
    "10": "https://cdn.discordapp.com/attachments/1424354249302609995/1425206806652649632/Untitled_design_10.png?ex=68e6bec5&is=68e56d45&hm=6295cccab9c4812ef685246b689a3a0f924fd1d0e9a1943f4de6732dfe34fe0c",
    "خد بس": "https://cdn.discordapp.com/attachments/1424354249302609995/1425206902563934338/Untitled_design_14.png?ex=68e6bedc&is=68e56d5c&hm=766f6d88ddc7490fe124a0797804453562e9ec14193fc0dc5f20b65736aaa99e",
    "خد وهات": "https://cdn.discordapp.com/attachments/1424354249302609995/1425206932821639290/Untitled_design_15.png?ex=68e6bee3&is=68e56d63&hm=a24a278539cf95a20e1d7cd700d51e8d6b2844525aea0a69ea89ef8c8387ad68",
    "سكرو أحمر": "https://cdn.discordapp.com/attachments/1424354249302609995/1425206946021249146/Untitled_design_16.png?ex=68e6bee6&is=68e56d66&hm=d75845ad99c2d8e00571c2758ac3c6ab496763c1f51242c687e226cbd06e4096",
    "+20": "https://cdn.discordapp.com/attachments/1423980365898580116/1425206381002363072/Untitled_design_1.png?ex=68e6be60&is=68e56ce0&hm=f978cc6d09bb2084cd586a2e19d7885ed2a5413fc5fc3448c6db042ed4e4f4a3",
    "كعب داير": "https://cdn.discordapp.com/attachments/1424354249302609995/1425206966443315311/Untitled_design_17.png?ex=68e6beeb&is=68e56d6b&hm=b046f5cdac8fa13fcefb1ec5b3702c8d3f33bbddbbc664f9944fee2385523717",
    "بصرة": "https://cdn.discordapp.com/attachments/1424354249302609995/1425206877955817502/Untitled_design_13.png?ex=68e6bed6&is=68e56d56&hm=d4c950dabea0cd175acaccd45c141cf892ed8cd68417d24f3516db060d119d1e",
    "الحرامي": "https://cdn.discordapp.com/attachments/1424354249302609995/1425206853612208279/Untitled_design_12.png?ex=68e6bed0&is=68e56d50&hm=59bf8e20dbe314572a606e67bfcd765685fb7b010d300df4eb2302855649b96f",
    "see swap": "https://cdn.discordapp.com/attachments/1424354249302609995/1425206826835902576/Untitled_design_11.png?ex=68e6beca&is=68e56d4a&hm=208f883442edb85cac5d5f9d6b3f219f4716203e79e732826fa671038c473259",
    # كروت مود التيمات (Teams Mode Cards)
    "بينج": "https://cdn.discordapp.com/attachments/1423980446382948373/1427996309960396841/Untitled_design.png?ex=68f0e4b3&is=68ef9333&hm=9770c3edb7f21554649e5941ba42e57381167a3d46310ab9b2d11a7d864f9712",
    "بونج": "https://cdn.discordapp.com/attachments/1423980446382948373/1427996309209743472/Untitled_design_2.png?ex=68f0e4b3&is=68ef9333&hm=3f1dedb244d82d384d79a1f64db9fcb0d621045be6a39a5678b430ac109fba15",
    "على كيفك": "https://cdn.discordapp.com/attachments/1423980446382948373/1427996309557612607/Untitled_design_1.png?ex=68f0e4b3&is=68ef9333&hm=099295ea2489178edd16e6f8758b0da9f60b828d5a4211ad0fadbd3b35852aa3"
}

# أسماء بديلة للكروت لضمان إيجاد الصور (تعامل مع اختلافات الكتابة)
CARD_ALIASES: dict[str, list[str]] = {
    # كشف ورقة
    "كشف ورقة": ["see swap"],
    "كشف ورقه": ["see swap"],
    "كشف ورقا": ["see swap"],
    "see swap": ["see swap"],
    # سكرو أزرق
    "سكرو ازرق": ["سكرو أزرق", "سكرو-أزرق", "سكرو از ر ق", "سكرو أخضر"],
    "سكرو أزرق": ["سكرو ازرق", "سكرو-أزرق", "سكرو أخضر"],
    "سكرو الأزرق": ["سكرو أزرق"],
    "سكرو الازرق": ["سكرو أزرق"],
    # تبديل
    "تبديل": ["بدل", "swap", "تبديل ورقة", "تبديل الورقة", "change"],
    # سكيب/تخطي
    "تخطي": ["سكيب", "skip"],
    "سكيب": ["تخطي", "skip"],
    # دبل
    "دبل": ["x2", "دوبل", "ضعف", "2x", "2X"],
    # +/- 10
    "+10": ["10+", "بلس 10", "زائد 10", "+ 10"],
    "-10": ["10-", "سالب 10", "- 10"],
}

def _normalize_text(s: str) -> str:
    try:
        s = s.strip()
        # توحيد بعض الحروف العربية الشائعة
        replacements = {
            "أ": "ا", "إ": "ا", "آ": "ا",
            "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي",
            "ـ": "",
        }
        for a, b in replacements.items():
            s = s.replace(a, b)
        # إزالة الرموز الشائعة في العناوين
        for ch in ["🃏", "🎴"]:
            s = s.replace(ch, "")
        return re.sub(r"\s+", " ", s)
    except Exception:
        return s

def get_card_description(card_name: str) -> str:
    if not isinstance(card_name, str):
        card_name = str(card_name)
    clean_name = card_name.strip().split('\n')[0].strip().replace('🃏', '').replace('🎴', '').strip()
    descriptions = {
        "-1": "🎯 ورقة سالب واحد — تخسر نقطة من مجموعك!",
        "1": "🔢 ورقة عادية بقيمة 1 نقطة", "2": "🔢 ورقة عادية بقيمة 2 نقطة", 
        "3": "🔢 ورقة عادية بقيمة 3 نقطة", "4": "🔢 ورقة عادية بقيمة 4 نقطة",
        "5": "🔢 ورقة عادية بقيمة 5 نقطة", "6": "🔢 ورقة عادية بقيمة 6 نقطة",
        "7": "👁️ ورقة تبصير — انظر إلى إحدى أوراقك", "8": "👁️ ورقة تبصير — انظر إلى إحدى أوراقك", 
        "9": "🔍 ورقة تفتيش — انظر إلى ورقة لاعب آخر", "10": "🔍 ورقة تفتيش — انظر إلى ورقة لاعب آخر",
        "خد بس": "🎁 هدية مجانية — أعط ورقة لأي لاعب", "خد وهات": "🔄 مبادلة — بدل ورقة مع لاعب آخر",
        "سكرو أحمر": "🚨 تحذير أحمر — قيمته عالية (25 نقطة)", "سكرو أخضر": "💚 سكرو آمن — قيمته صفر (آمن)",
        "+20": "📈 ورقة صعود — تضيف 20 نقطة (خطيرة!)", "كعب داير": "🎪 سيرك البطاقات — اختر من عدة خيارات",
        "بصرة": "🎯 رمية دقيقة — تخلص من ورقة غير مرغوب فيها", "الحرامي": "🦹 ورقة اللص — قد تكسب أو تخسر نقاطاً",
    "see swap": "👀 نظرة ومبادلة — انظر وقرر إذا كنت تريد المبادلة",
    "كشف ورقة": "👀 نظرة ومبادلة — (مرادف see swap)",
        # كروت مود التيمات
        "بينج": "🏓 كرت بينج — تخطي دور اللاعب التالي من الفريق الخصم! يمكن للزميل الرد ببونج",
        "بونج": "🥁 كرت بونج — الرد المثالي على بينج! استخدمه كتبصير بعد بينج زميلك",
        "على كيفك": "🎲 كرت على كيفك — اختر أي نوع كرت تريد نسخه! قوة مطلقة",
    }
    if clean_name in descriptions:
        return descriptions[clean_name]
    if clean_name.isdigit():
        return f"🔢 ورقة عادية بقيمة {clean_name} نقطة"
    return "🎴 ورقة عادية — بدون تأثير خاص"

IMAGES_DIR = Path(__file__).parent

def build_image_map(images_dir: Path):
    """بناء خريطة الصور المحلية"""
    imgs = {}
    try:
        # مجلدات شائعة للصور
        candidate_dirs = [
            images_dir,
            images_dir / "images",
            images_dir / "imgs",
            images_dir / "assets",
            images_dir / "cards",
            images_dir / "صور",
            images_dir / "كروت",
        ]
        seen = set()
        for base in candidate_dirs:
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if not p.is_file():
                    continue
                ext = p.suffix.lower()
                if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".jfif"):
                    key = p.stem
                    # تجنب الكتابة على نفس المفتاح من مسارات مختلفة
                    if key in imgs:
                        # فضّل الملف الأقرب للمجلد الرئيسي
                        try:
                            if str(p).count(os.sep) < str(imgs[key]).count(os.sep):
                                imgs[key] = p
                        except Exception:
                            pass
                    else:
                        imgs[key] = p
                    if key not in seen:
                        logger.debug(f"📁 Found local image: {key}{p.suffix} @ {p}")
                        seen.add(key)
    except Exception as e:
        logger.error(f"Error building image map: {e}")
    return imgs

CARD_IMAGE_FILES = build_image_map(IMAGES_DIR)
logger.info(f"🖼️  Loaded {len(CARD_IMAGE_FILES)} local card images")

def reload_card_images():
    global CARD_IMAGE_FILES
    try:
        CARD_IMAGE_FILES = build_image_map(IMAGES_DIR)
        logger.info(f"🔁 Reloaded local card images: {len(CARD_IMAGE_FILES)} files")
    except Exception as e:
        logger.error(f"Failed to reload images: {e}")

def card_image_path_for(card_str: str, *, _rescan_on_miss: bool = True):
    def _lookup() -> Optional[Path]:
        key = card_key(card_str)
        # 1) مطابقة مباشرة
        p = CARD_IMAGE_FILES.get(key)
        if p:
            return p
        # 2) عبر الأسماء البديلة
        alts = CARD_ALIASES.get(key) or []
        for alt in alts:
            p = CARD_IMAGE_FILES.get(alt)
            if p:
                return p
        # 3) عبر التطبيع المبسط
        norm_key = _normalize_text(key)
        for k, path in CARD_IMAGE_FILES.items():
            if _normalize_text(k) == norm_key:
                return path
        # 4) الاسم البديل بعد التطبيع
        for alt in alts:
            norm_alt = _normalize_text(alt)
            for k, path in CARD_IMAGE_FILES.items():
                if _normalize_text(k) == norm_alt:
                    return path
        # 5) fallback للأرقام مع +/-
        m = re.match(r"^[+-](\d+)$", key)
        if m:
            base_num = m.group(1)
            p = CARD_IMAGE_FILES.get(base_num)
            if p:
                return p
        return None

    pth = _lookup()
    if pth is None and _rescan_on_miss:
        # أعد التحميل مرة واحدة إذا لم نجد الصورة (في حال أضيفت صور أثناء التشغيل)
        reload_card_images()
        pth = card_image_path_for(card_str, _rescan_on_miss=False)
    return pth

def card_image_url_for(card_str: str):
    key = card_key(card_str)
    # 1) مطابقة مباشرة
    url = CARD_IMAGES.get(key)
    if url:
        return url
    # 2) عبر الأسماء البديلة
    alts = CARD_ALIASES.get(key) or []
    for alt in alts:
        url = CARD_IMAGES.get(alt)
        if url:
            return url
    # 3) عبر التطبيع المبسط
    norm_key = _normalize_text(key)
    for k, u in CARD_IMAGES.items():
        if _normalize_text(k) == norm_key:
            return u
    # 4) الاسم البديل بعد التطبيع
    for alt in alts:
        norm_alt = _normalize_text(alt)
        for k, u in CARD_IMAGES.items():
            if _normalize_text(k) == norm_alt:
                return u
    # 5) fallback للأرقام مع +/-
    m = re.match(r"^[+-](\d+)$", key)
    if m:
        base_num = m.group(1)
        u = CARD_IMAGES.get(base_num)
        if u:
            return u
    return None

# تقرير سريع عن الصور المفقودة مقارنة بالكروت المتاحة
@bot.command(name="imgmissing")
async def cmd_img_missing(ctx):
    if not is_owner(ctx.author):
        return await ctx.send("❌ هذا الأمر للأونر فقط")
    reload_card_images()
    expected = set(name for name, _ in deck_list)
    # أضف أيضاً بعض الأسماء الخاصة الموجودة في CARD_IMAGES
    expected |= set(CARD_IMAGES.keys())
    have = set(CARD_IMAGE_FILES.keys())
    missing = sorted([x for x in expected if card_image_path_for(x, _rescan_on_miss=False) is None])
    if not missing:
        return await ctx.send("✅ كل الصور متوفرة محليًا")
    # اعرض أول 30 فقط لتفادي السبام
    preview = "\n".join(f"• {m}" for m in missing[:30])
    more = len(missing) - 30
    msg = f"❌ عدد الصور المفقودة: {len(missing)}\n{preview}"
    if more > 0:
        msg += f"\n… وغيرها {more}"
    await ctx.send(msg)

# أمر لإعادة تحميل الصور يدوياً (Owner فقط)
@bot.command(name="reloadimages")
async def cmd_reload_images(ctx):
    if not is_owner(ctx.author):
        return await ctx.send("❌ هذا الأمر للأونر فقط")
    before = len(CARD_IMAGE_FILES)
    reload_card_images()
    after = len(CARD_IMAGE_FILES)
    await ctx.send(f"🔁 تم إعادة تحميل الصور: {before} ➜ {after}")

async def send_card(destination, card_str, title=None, interaction=None, ephemeral=False):
    try:
        # استخراج اسم الكرت
        if isinstance(card_str, tuple):
            card_name = str(card_str[0])
        else:
            card_name = str(card_str)
        
        clean_name = card_name.split("\n")[0].strip()
        description = get_card_description(clean_name)
        
        # إنشاء الـ Embed
        embed = discord.Embed(
            title=title or f"🎴 {clean_name}",
            description=f"📝 {description}",
            color=discord.Color.random()
        )
        
        # محاولة استخدام ملف محلي أولاً (أفضل وأسرع)
        img_path = card_image_path_for(card_str)
        if img_path and img_path.exists():
            try:
                filename = img_path.name
                file = discord.File(fp=str(img_path), filename=filename)
                embed.set_image(url=f"attachment://{filename}")
                logger.info(f"🎴 Sending card '{clean_name}' with local image file: {filename}")
                
                if interaction:
                    is_done = interaction.response.is_done()
                    if is_done:
                        await interaction.followup.send(embed=embed, file=file, ephemeral=ephemeral)
                    else:
                        await interaction.response.send_message(embed=embed, file=file, ephemeral=ephemeral)
                elif destination:
                    await destination.send(embed=embed, file=file)
                return
            except Exception as e:
                logger.warning(f"Failed to send local image file: {e}")
        
        # Fallback: استخدام URL من الـ dictionary
        image_url = card_image_url_for(card_str)
        if image_url:
            embed.set_image(url=image_url)
            logger.info(f"🎴 Sending card '{clean_name}' with CDN URL (may be expired)")
            
            if interaction:
                is_done = interaction.response.is_done()
                if is_done:
                    await interaction.followup.send(embed=embed, ephemeral=ephemeral)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            elif destination:
                await destination.send(embed=embed)
            return
        
        # إذا مافيش صورة خالص، نرسل الـ embed بدون صورة
        logger.warning(f"⚠️ No image found for card '{clean_name}'")
        if interaction:
            is_done = interaction.response.is_done()
            if is_done:
                await interaction.followup.send(embed=embed, ephemeral=ephemeral)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
        elif destination:
            await destination.send(embed=embed)
            
    except discord.Forbidden:
        logger.warning("Missing permissions to send card message")
    except discord.HTTPException as e:
        logger.error(f"HTTP error sending card: {str(e)}")
    except Exception as e:
        try:
            name_safe = clean_name if 'clean_name' in locals() else str(card_str)
            logger.error(f"Unexpected error sending card {name_safe}: {str(e)}")
        except Exception:
            logger.error(f"Unexpected error sending card: {str(e)}")
        # محاولة إرسال رسالة بديلة
        try:
            if interaction and not interaction.response.is_done():
                await interaction.response.send_message("❌ حدث خطأ في عرض الورقة", ephemeral=True)
            elif destination:
                await destination.send(f"🎴 {clean_name if 'clean_name' in locals() else 'كرت'}")
        except Exception:
            pass

# -----------------------------
# تشغيل البوت
# -----------------------------
# حماية التوكن - استخدم متغير البيئة DISCORD_TOKEN أو ملف .env/ token.txt محلياً

def _load_dotenv_if_exists():
    try:
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            for raw in env_path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and v:
                        os.environ.setdefault(k, v)
    except Exception:
        pass

_load_dotenv_if_exists()
_ENV_TOKEN = os.getenv("DISCORD_TOKEN")

#Fallback: token.txt (للاستخدام المحلي فقط)
if not _ENV_TOKEN:
    try:
        token_file = Path(__file__).parent / "token.txt"
        if token_file.exists():
            _ENV_TOKEN = token_file.read_text(encoding="utf-8").strip()
    except Exception:
        _ENV_TOKEN = None

if not _ENV_TOKEN:
    print("❌ خطأ: لم يتم العثور على توكن البوت.")
    print("💡 طرق الحل:")
    print("   • ضع التوكن في متغير البيئة DISCORD_TOKEN")
    print("   • أو أنشئ ملف .env يحتوي: DISCORD_TOKEN=your_token_here")
    print("   • أو أنشئ ملف token.txt وضع داخله التوكن (للاستخدام المحلي)")
    # تلميح لبيئة Windows PowerShell
    print("\nمثال Windows PowerShell:")
    print("   setx DISCORD_TOKEN \"your_token_here\"")
    print("ثم افتح نافذة PowerShell جديدة وشغل السكربت مرة أخرى.")
    raise SystemExit(1)

try:
    print("🚀 بدء تشغيل البوت...")
    bot.run(_ENV_TOKEN)
except discord.LoginFailure:
    print("❌ خطأ في تسجيل الدخول: التوكن غير صحيح!")
except Exception as e:
    print(f"❌ خطأ في تشغيل البوت: {e}")