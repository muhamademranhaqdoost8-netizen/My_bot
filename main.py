import os
import glob
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import yt_dlp

def download_media(url: str) -> list:
    os.makedirs("downloads", exist_ok=True)
    
    # دانلود هوشمند بهترین کیفیت موجود و ترکیب صدا و تصویر
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'max_filesize': 48 * 1024 * 1024,  # حداکثر حجم برای تلگرام
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if 'entries' in info:
            downloaded_files = []
            for entry in info['entries']:
                file_id = entry.get('id', 'media')
                found = glob.glob(f"downloads/{file_id}*")
                downloaded_files.extend(found)
            return downloaded_files
        else:
            file_id = info.get('id', 'media')
            return glob.glob(f"downloads/{file_id}*")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"سلام **{user_name}** عزیز! 👋\n\n"
        "به ربات هوشمند و سریع دانلودر خوش آمدید.\n"
        "✨ طراحی و توسعه توسط: **عمران نوری**\n\n"
        "🚀 **راهنما: کافیست هر زمان لینک هر ویدیویی از یوتیوب یا اینستاگرام را مستقیم به اینجا بفرستید تا فوراً با بالاترین کیفیت برایتان دانلود و ارسال شود!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # بررسی اینکه آیا پیام فرستاده شده لینک است یا خیر
    if not (text.startswith("http://") or text.startswith("https://")):
        await update.message.reply_text("⚠️ لطفاً یک لینک معتبر ارسال کنید (مثلاً لینکی که با https شروع می‌شود).")
        return

    status_msg = await update.message.reply_text("⏳ در حال دانلود با بالاترین کیفیت... لطفاً کمی صبر کنید.")
    
    try:
        files = download_media(text)
        if files:
            await status_msg.edit_text("⬆️ در حال ارسال به تلگرام...")
            for f in files:
                with open(f, 'rb') as media_file:
                    if f.endswith(('.jpg', '.png', '.jpeg', '.webp')):
                        await update.message.reply_photo(photo=media_file)
                    elif f.endswith(('.mp3', '.m4a', '.aac', '.opus')):
                        await update.message.reply_audio(audio=media_file)
                    else:
                        await update.message.reply_video(video=media_file)
            
            await update.message.reply_text(
                "✨ **دانلود با موفقیت انجام شد!**\nهر لینک دیگری دارید بفرستید.",
                parse_mode="Markdown"
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ خطا: فایلی برای دانلود یافت نشد.")
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در دانلود: {str(e)[:100]}")
    finally:
        # پاک‌سازی فایل‌های موقت
        for f in glob.glob("downloads/*"):
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    BOT_TOKEN = "8876033736:AAH-EoESxq8aTDDMJE3gtxOC7hOZ2x0e5wg"  # توکن ربات خود را اینجا بگذارید

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # هندلر دستور استارت
    app.add_handler(CommandHandler('start', start))
    
    # دریافت خودکار هرگونه لینک متنی بدون نیاز به استارت مجدد
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("ربات روشن شد!")
    app.run_polling()

