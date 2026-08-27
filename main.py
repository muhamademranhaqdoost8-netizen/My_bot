import os
import re
import glob
import uuid
import asyncio
import shutil
import logging
from pathlib import Path

import yt_dlp

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("8876033736:AAH-EoESxq8aTDDMJE3gtxOC7hOZ2x0e5wg")

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

GET_LINK = 1

MAX_FILE_SIZE = 49 * 1024 * 1024  # حدود 49MB

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================
# KEYBOARD
# =========================

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📥 دانلود ویدیو از یوتیوب",
                callback_data="opt_yt_video"
            )
        ],
        [
            InlineKeyboardButton(
                "🎵 دانلود آهنگ از یوتیوب",
                callback_data="opt_yt_audio"
            )
        ],
        [
            InlineKeyboardButton(
                "📸 دانلود از اینستاگرام",
                callback_data="opt_insta"
            )
        ],
    ])


# =========================
# URL DETECTION
# =========================

def is_youtube(url: str) -> bool:
    return bool(
        re.search(
            r"(youtube\.com|youtu\.be)",
            url,
            re.IGNORECASE
        )
    )


def is_instagram(url: str) -> bool:
    return bool(
        re.search(
            r"(instagram\.com)",
            url,
            re.IGNORECASE
        )
    )


# =========================
# DOWNLOAD
# =========================

def download_media(url: str, mode: str, user_id: int):
    """
    mode:
        video
        audio

    Returns:
        downloaded file path
    """

    job_id = uuid.uuid4().hex
    user_dir = DOWNLOAD_DIR / str(user_id) / job_id
    user_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(
        user_dir / "%(title).80s_%(id)s.%(ext)s"
    )

    # -------------------------
    # YouTube
    # -------------------------

    if is_youtube(url):

        if mode == "audio":

            ydl_opts = {
                "format": "bestaudio/best",

                "outtmpl": output_template,

                "noplaylist": True,

                "quiet": True,

                "no_warnings": True,

                "restrictfilenames": True,

                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],

                "retries": 3,

                "fragment_retries": 3,

                "socket_timeout": 30,

            }

        else:

            ydl_opts = {
                # Video + Audio
                "format": (
                    "bv*[ext=mp4]+ba[ext=m4a]/"
                    "bv*+ba/b"
                ),

                "outtmpl": output_template,

                "merge_output_format": "mp4",

                "noplaylist": True,

                "quiet": True,

                "no_warnings": True,

                "restrictfilenames": True,

                "retries": 3,

                "fragment_retries": 3,

                "socket_timeout": 30,

            }

    # -------------------------
    # Instagram
    # -------------------------

    elif is_instagram(url):

        ydl_opts = {
            "format": "best",

            "outtmpl": output_template,

            "noplaylist": True,

            "quiet": True,

            "no_warnings": True,

            "restrictfilenames": True,

            "retries": 3,

            "fragment_retries": 3,

            "socket_timeout": 30,
        }

    else:
        shutil.rmtree(user_dir, ignore_errors=True)
        raise ValueError(
            "لینک فقط باید مربوط به YouTube یا Instagram باشد."
        )

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            if not info:
                raise Exception(
                    "اطلاعات ویدیو دریافت نشد."
                )

        # پیدا کردن فایل خروجی
        files = [
            p for p in user_dir.iterdir()
            if p.is_file()
        ]

        if not files:
            raise Exception(
                "فایل دانلود شده پیدا نشد."
            )

        # بزرگ‌ترین فایل را انتخاب می‌کنیم
        files.sort(
            key=lambda x: x.stat().st_size,
            reverse=True
        )

        final_file = files[0]

        # بررسی حجم
        if final_file.stat().st_size > MAX_FILE_SIZE:
            raise Exception(
                "حجم فایل بیشتر از محدودیت ارسال ربات است."
            )

        return final_file, user_dir

    except Exception:

        shutil.rmtree(
            user_dir,
            ignore_errors=True
        )

        raise


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    name = user.first_name or "دوست عزیز"

    text = (
        f"سلام **{name}** عزیز! 👋\n\n"
        "به ربات دانلودر خوش آمدید. 🚀\n\n"
        "✨ طراحی و اجرا توسط: **عمران نوری**\n\n"
        "لطفاً نوع دانلود را انتخاب کنید:"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

    return GET_LINK


# =========================
# MENU
# =========================

async def menu_click(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    data = query.data

    if data == "opt_yt_video":

        context.user_data["mode"] = "video"

        await query.message.reply_text(
            "📥 لینک ویدیوی YouTube را ارسال کنید:"
        )

    elif data == "opt_yt_audio":

        context.user_data["mode"] = "audio"

        await query.message.reply_text(
            "🎵 لینک ویدیوی YouTube را ارسال کنید تا "
            "به MP3 تبدیل شود:"
        )

    elif data == "opt_insta":

        context.user_data["mode"] = "video"

        await query.message.reply_text(
            "📸 لینک پست یا Reel اینستاگرام را ارسال کنید:"
        )

    return GET_LINK


# =========================
# RECEIVE LINK
# =========================

async def receive_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.text:
        return GET_LINK

    url = update.message.text.strip()

    if not url.startswith(("http://", "https://")):

        await update.message.reply_text(
            "⚠️ لطفاً لینک معتبر ارسال کنید."
        )

        return GET_LINK

    if not is_youtube(url) and not is_instagram(url):

        await update.message.reply_text(
            "❌ این لینک مربوط به YouTube یا Instagram نیست."
        )

        return GET_LINK

    mode = context.user_data.get(
        "mode",
        "video"
    )

    status = await update.message.reply_text(
        "⏳ در حال دریافت اطلاعات و دانلود...\n"
        "لطفاً صبر کنید."
    )

    user_id = update.effective_user.id

    try:

        await update.message.chat.send_action(
            action=ChatAction.UPLOAD_VIDEO
        )

        # yt-dlp blocking است؛
        # آن را داخل thread اجرا می‌کنیم
        file_path, job_dir = await asyncio.to_thread(
            download_media,
            url,
            mode,
            user_id
        )

        await status.edit_text(
            "⬆️ دانلود انجام شد.\n"
            "در حال ارسال فایل به تلگرام..."
        )

        # -------------------------
        # AUDIO
        # -------------------------

        if mode == "audio":

            with open(file_path, "rb") as audio:

                await update.message.reply_audio(
                    audio=audio,
                    caption="🎵 دانلود با موفقیت انجام شد."
                )

        # -------------------------
        # VIDEO
        # -------------------------

        else:

            with open(file_path, "rb") as video:

                await update.message.reply_video(
                    video=video,
                    supports_streaming=True,
                    caption="🎬 دانلود با موفقیت انجام شد."
                )

        await status.delete()

        await update.message.reply_text(
            "✨ گزینه بعدی را انتخاب کنید:",
            reply_markup=main_keyboard()
        )

        # پاک کردن فایل
        shutil.rmtree(
            job_dir,
            ignore_errors=True
        )

    except Exception as e:

        logger.exception(
            "Download error"
        )

        error_text = str(e)

        # خطاهای رایج
        if "Requested format is not available" in error_text:

            message = (
                "❌ فرمت مناسب این ویدیو پیدا نشد.\n\n"
                "لطفاً یک ویدیوی دیگر امتحان کنید."
            )

        elif "Tunnel connection failed" in error_text:

            message = (
                "🌐 اتصال سرور به سرویس مقصد برقرار نشد.\n\n"
                "لطفاً چند لحظه بعد دوباره امتحان کنید."
            )

        elif "Sign in to confirm" in error_text:

            message = (
                "🔐 YouTube دسترسی این ویدیو را محدود کرده است."
            )

        elif "Private" in error_text:

            message = (
                "🔒 این محتوا خصوصی است."
            )

        elif "Unsupported URL" in error_text:

            message = (
                "❌ لینک پشتیبانی نمی‌شود."
            )

        elif "File size" in error_text:

            message = (
                "📦 حجم فایل برای ارسال در تلگرام زیاد است."
            )

        else:

            message = (
                "❌ دانلود انجام نشد.\n\n"
                "لطفاً لینک دیگری امتحان کنید."
            )

        try:

            await status.edit_text(
                message
            )

        except Exception:
            pass

    finally:

        # پاکسازی فایل‌های باقی‌مانده
        user_folder = DOWNLOAD_DIR / str(user_id)

        if user_folder.exists():

            for item in user_folder.iterdir():

                if item.is_dir():

                    shutil.rmtree(
                        item,
                        ignore_errors=True
                    )

    return GET_LINK


# =========================
# CANCEL
# =========================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "❌ عملیات لغو شد."
    )

    return ConversationHandler.END


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN در Environment Variables تنظیم نشده است."
        )

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    conversation = ConversationHandler(

        entry_points=[
            CommandHandler(
                "start",
                start
            )
        ],

        states={

            GET_LINK: [

                CallbackQueryHandler(
                    menu_click,
                    pattern=r"^opt_"
                ),

                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_link
                ),

            ]

        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel
            ),

            CommandHandler(
                "start",
                start
            ),
        ],

        allow_reentry=True,
    )

    app.add_handler(
        conversation
    )

    logger.info(
        "BOT STARTED"
    )

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
