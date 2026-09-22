import os
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6189261314
REQUIRED_REFERRALS = 5
DEFAULT_CHANNEL = "@Super_Jinx"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set.")

db = sqlite3.connect("super_panel.db", check_same_thread=False)
db.row_factory = sqlite3.Row

db.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    referrer_id INTEGER,
    referrals INTEGER DEFAULT 0,
    panels INTEGER DEFAULT 0,
    claimed_panels INTEGER DEFAULT 0
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS referrals(
    invited_id INTEGER PRIMARY KEY,
    referrer_id INTEGER NOT NULL
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS channels(
    channel TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 1
)
""")

db.execute(
    "INSERT OR IGNORE INTO channels(channel,enabled) VALUES(?,1)",
    (DEFAULT_CHANNEL,)
)
db.commit()

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


def user(uid):
    return db.execute(
        "SELECT * FROM users WHERE user_id=?",
        (uid,)
    ).fetchone()


def channels():
    return [
        r["channel"]
        for r in db.execute(
            "SELECT channel FROM channels WHERE enabled=1"
        ).fetchall()
    ]


def home_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔥 دعوت کن و پنل بگیر",
                callback_data="invite"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 رفرال‌های من",
                callback_data="refs"
            ),
            InlineKeyboardButton(
                text="🎁 جوایز من",
                callback_data="rewards"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 وضعیت حساب",
                callback_data="account"
            )
        ],
        [
            InlineKeyboardButton(
                text="📢 کانال رسمی",
                url="https://t.me/Super_Jinx"
            )
        ]
    ])


def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📊 آمار ربات",
                callback_data="astats"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 کاربران و رفرال‌ها",
                callback_data="ausers"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔐 عضویت اجباری",
                callback_data="channels"
            )
        ],
        [
            InlineKeyboardButton(
                text="📨 ارسال پیام هماهنگی",
                callback_data="broadcast"
            )
        ]
    ])


async def joined(uid):
    for ch in channels():
        try:
            member = await bot.get_chat_member(ch, uid)

            if member.status in ("left", "kicked"):
                return False

        except Exception:
            return False

    return True


def join_kb():
    rows = []

    for channel in channels():
        rows.append([
            InlineKeyboardButton(
                text=f"📢 عضویت در {channel}",
                url=f"https://t.me/{channel.lstrip('@')}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            text="✅ بررسی عضویت",
            callback_data="check"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_home(target):
    u = user(target.from_user.id)

    count = u["referrals"]
    remaining = max(REQUIRED_REFERRALS - count, 0)

    filled = min(
        10,
        int(count / REQUIRED_REFERRALS * 10)
    )

    bar = "█" * filled + "░" * (10 - filled)

    await target.answer(
        f"╭━━━━━━━━━━━━━━━━━━━━╮\n"
        f"       ⚡ <b>SUPER PANEL</b>\n"
        f"     <i>CONTROL CENTER</i>\n"
        f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
        f"👋 خوش اومدی <b>{u['first_name']}</b>\n\n"
        f"🎁 هر <b>۵ دعوت موفق</b> = یک پنل رایگان!\n\n"
        f"👥 دعوت‌های موفق: "
        f"<b>{count} / {REQUIRED_REFERRALS}</b>\n"
        f"{bar}\n\n"
        f"🔥 "
        f"{'🎉 جایزه آماده است!' if remaining == 0 else f'فقط {remaining} نفر تا جایزه'}",
        reply_markup=home_kb(),
        parse_mode="HTML"
    )


@dp.message(CommandStart())
async def start(m: Message):
    old = user(m.from_user.id)

    ref = None

    parts = m.text.split(maxsplit=1)

    if len(parts) == 2 and parts[1].startswith("ref_"):
        try:
            ref = int(parts[1][4:])
        except ValueError:
            ref = None

    if not old:
        db.execute(
            """
            INSERT INTO users(
                user_id,
                username,
                first_name,
                referrer_id
            )
            VALUES(?,?,?,?)
            """,
            (
                m.from_user.id,
                m.from_user.username or "",
                m.from_user.first_name or "",
                ref
            )
        )

        db.commit()

        if ref and ref != m.from_user.id:

            exists = db.execute(
                "SELECT 1 FROM referrals WHERE invited_id=?",
                (m.from_user.id,)
            ).fetchone()

            if not exists and user(ref):

                db.execute(
                    """
                    INSERT INTO referrals(
                        invited_id,
                        referrer_id
                    )
                    VALUES(?,?)
                    """,
                    (m.from_user.id, ref)
                )

                db.execute(
                    """
                    UPDATE users
                    SET referrals=referrals+1
                    WHERE user_id=?
                    """,
                    (ref,)
                )

                db.commit()

                rc = user(ref)["referrals"]

                await bot.send_message(
                    ref,
                    f"🎉 <b>یک شخص جدید به رفرال شما اضافه شد!</b>\n\n"
                    f"👤 {m.from_user.first_name}\n"
                    f"🆔 <code>{m.from_user.id}</code>\n"
                    f"👥 رفرال شما: <b>{rc}/5</b>\n\n"
                    f"{'🎁 یک پنل برای شما فعال شد!' if rc == 5 else ''}",
                    parse_mode="HTML"
                )

                if rc == 5:
                    db.execute(
                        """
                        UPDATE users
                        SET panels=panels+1
                        WHERE user_id=?
                        """,
                        (ref,)
                    )

                    db.commit()

    if not await joined(m.from_user.id):

        await m.answer(
            "🔐 <b>ابتدا عضو کانال شوید</b>\n\n"
            "بعد روی بررسی عضویت بزنید.",
            reply_markup=join_kb(),
            parse_mode="HTML"
        )

        return

    await send_home(m)


@dp.callback_query(F.data == "check")
async def check(c: CallbackQuery):

    if not await joined(c.from_user.id):
        await c.answer(
            "❌ هنوز عضویت شما تأیید نشده.",
            show_alert=True
        )
        return

    await c.message.delete()

    await send_home(c.message)

    await c.answer("✅ عضویت تأیید شد.")


@dp.callback_query(F.data == "invite")
async def invite(c: CallbackQuery):

    me = await bot.get_me()
    u = user(c.from_user.id)

    link = (
        f"https://t.me/{me.username}"
        f"?start=ref_{c.from_user.id}"
    )

    await c.message.edit_text(
        f"🔥 <b>INVITE & EARN</b>\n\n"
        f"🎯 پیشرفت: <b>{u['referrals']}/5</b>\n"
        f"🔗 لینک اختصاصی:\n"
        f"<code>{link}</code>\n\n"
        f"هر کاربر جدید فقط یک‌بار برای معرف حساب می‌شود.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 کپی/اشتراک لینک",
                        switch_inline_query=link
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 بازگشت",
                        callback_data="home"
                    )
                ]
            ]
        ),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "home")
async def home(c: CallbackQuery):

    if not await joined(c.from_user.id):

        await c.message.edit_text(
            "🔐 ابتدا عضو کانال شوید.",
            reply_markup=join_kb()
        )

        return

    u = user(c.from_user.id)

    count = u["referrals"]
    remaining = max(5 - count, 0)

    filled = min(
        10,
        int(count / 5 * 10)
    )

    bar = "█" * filled + "░" * (10 - filled)

    await c.message.edit_text(
        f"╭━━━━━━━━━━━━━━━━━━━━╮\n"
        f"       ⚡ <b>SUPER PANEL</b>\n"
        f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
        f"👋 {u['first_name']}\n"
        f"🎁 هر ۵ دعوت موفق = پنل رایگان\n\n"
        f"👥 <b>{count}/5</b>\n"
        f"{bar}\n\n"
        f"🔥 "
        f"{'🎉 جایزه آماده است!' if remaining == 0 else f'فقط {remaining} نفر تا جایزه'}",
        reply_markup=home_kb(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "refs")
async def refs(c: CallbackQuery):

    rows = db.execute(
        """
        SELECT
            u.first_name,
            u.username,
            u.user_id
        FROM referrals r
        JOIN users u
            ON u.user_id=r.invited_id
        WHERE r.referrer_id=?
        """,
        (c.from_user.id,)
    ).fetchall()

    text = "👥 <b>رفرال‌های من</b>\n\n"

    text += (
        "\n".join(
            f"{i}. {r['first_name']} — "
            f"<code>{r['user_id']}</code>"
            for i, r in enumerate(rows, 1)
        )
        or "هنوز رفرالی ثبت نشده."
    )

    await c.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 بازگشت",
                        callback_data="home"
                    )
                ]
            ]
        ),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "rewards")
async def rewards(c: CallbackQuery):

    u = user(c.from_user.id)

    await c.message.edit_text(
        f"🎁 <b>جوایز من</b>\n\n"
        f"🏆 پنل‌های آماده: <b>{u['panels']}</b>\n"
        f"✅ پنل‌های دریافت‌شده: "
        f"<b>{u['claimed_panels']}</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 بازگشت",
                        callback_data="home"
                    )
                ]
            ]
        ),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "account")
async def account(c: CallbackQuery):

    u = user(c.from_user.id)

    await c.message.edit_text(
        f"📊 <b>وضعیت حساب</b>\n\n"
        f"👤 {u['first_name']}\n"
        f"🆔 <code>{u['user_id']}</code>\n"
        f"👥 رفرال: <b>{u['referrals']}/5</b>\n"
        f"🎁 پنل آماده: <b>{u['panels']}</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 بازگشت",
                        callback_data="home"
                    )
                ]
            ]
        ),
        parse_mode="HTML"
    )


@dp.message(Command("admin"))
async def admin(m: Message):

    if m.from_user.id == ADMIN_ID:

        await m.answer(
            "⚙️ <b>ADMIN PANEL</b>",
            reply_markup=admin_kb(),
            parse_mode="HTML"
        )


@dp.callback_query(F.data == "astats")
async def astats(c: CallbackQuery):

    if c.from_user.id != ADMIN_ID:
        return

    users = db.execute(
        "SELECT COUNT(*) n FROM users"
    ).fetchone()["n"]

    refs = db.execute(
        "SELECT COUNT(*) n FROM referrals"
    ).fetchone()["n"]

    await c.message.edit_text(
        f"📊 <b>آمار</b>\n\n"
        f"👥 کاربران: <b>{users}</b>\n"
        f"🔗 رفرال موفق: <b>{refs}</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 مدیریت",
                        callback_data="admin"
                    )
                ]
            ]
        ),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "ausers")
async def ausers(c: CallbackQuery):

    if c.from_user.id != ADMIN_ID:
        return

    rows = db.execute(
        """
        SELECT
            first_name,
            user_id,
            referrals
        FROM users
        WHERE referrals>0
        ORDER BY referrals DESC
        LIMIT 20
        """
    ).fetchall()

    text = "👥 <b>کاربران دارای رفرال</b>\n\n"

    text += (
        "\n\n".join(
            f"{i}. {r['first_name']} — "
            f"<code>{r['user_id']}</code>\n"
            f"🔥 {r['referrals']} رفرال"
            for i, r in enumerate(rows, 1)
        )
        or "موردی نیست."
    )

    await c.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 مدیریت",
                        callback_data="admin"
                    )
                ]
            ]
        ),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "channels")
async def channel_menu(c: CallbackQuery):

    if c.from_user.id != ADMIN_ID:
        return

    channel_list = channels()

    text = "🔐 <b>عضویت اجباری</b>\n\n"

    if channel_list:
        text += "\n".join(
            f"🟢 {x}"
            for x in channel_list
        )
    else:
        text += "هیچ کانالی ثبت نشده."

    await c.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ افزودن کانال",
                        callback_data="addch"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑 حذف Super_Jinx",
                        callback_data="deldefault"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 مدیریت",
                        callback_data="admin"
                    )
                ]
            ]
        ),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "deldefault")
async def deldefault(c: CallbackQuery):

    if c.from_user.id != ADMIN_ID:
        return

    db.execute(
        "DELETE FROM channels WHERE channel=?",
        (DEFAULT_CHANNEL,)
    )

    db.commit()

    await c.answer(
        "کانال حذف شد.",
        show_alert=True
    )

    await channel_menu(c)


@dp.callback_query(F.data == "addch")
async def addch(c: CallbackQuery):

    if c.from_user.id != ADMIN_ID:
        return

    await c.message.answer(
        "➕ آیدی کانال را در پیام بعدی بفرست، "
        "مثل @ExampleChannel"
    )

    dp.message.register(
        addch_message,
        F.from_user.id == ADMIN_ID
    )


async def addch_message(m: Message):

    ch = m.text.strip()

    if not ch.startswith("@"):
        ch = "@" + ch

    db.execute(
        """
        INSERT OR REPLACE INTO channels(
            channel,
            enabled
        )
        VALUES(?,1)
        """,
        (ch,)
    )

    db.commit()

    await m.answer(
        f"✅ {ch} اضافه شد."
    )


@dp.callback_query(F.data == "admin")
async def admin_back(c: CallbackQuery):

    if c.from_user.id == ADMIN_ID:

        await c.message.edit_text(
            "⚙️ <b>ADMIN PANEL</b>",
            reply_markup=admin_kb(),
            parse_mode="HTML"
        )


async def main():

    print("SUPER PANEL is running...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())