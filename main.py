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
    
    # دانلود مستقیم بدون هیچ‌گونه فیلتر یا شرط کیفیت
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'max_filesize': 48 * 1024 * 1024,  # سقف مجاز تلگرام
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
        "به ربات هوشمند دانلودر خوش آمدید.\n"
        "✨ طراحی و توسعه توسط: **عمران نوری**\n\n"
        "🚀 از این پس فقط کافیست لینک مورد نظرتان را بفرستید تا بلافاصله دانلود و برای شما ارسال شود!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # بررسی لینک بودن متن
    if not (text.startswith("http://") or text.startswith("https://")):
        await update.message.reply_text("⚠️ لطفاً یک لینک معتبر ارسال کنید.")
        return

    status_msg = await update.message.reply_text("⏳ در حال دانلود... لطفاً کمی صبر کنید.")
    
    try:
        files = download_media(text)
        if files:
            await status_msg.edit_text("⬆️ در حال ارسال به تلگرام...")
            for f in files:
                with open(f, 'rb') as media_file:
                    if f.endswith(('.jpg', '.png', '.jpeg', '.webp')):
                        await update.message.reply_photo(photo=media_file)
                    elif f.endswith(('.mp3', '.m4a', '.aac', '.opus', '.wav', '.ogg')):
                        await update.message.reply_audio(audio=media_file)
                    else:
                        await update.message.reply_video(video=media_file)
            
            await update.message.reply_text(
                "✨ **دانلود با موفقیت انجام شد!**",
                parse_mode="Markdown"
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ خطا: فایلی یافت نشد.")
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا: {str(e)[:100]}")
    finally:
        # پاک‌سازی حافظه موقت
        for f in glob.glob("downloads/*"):
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    BOT_TOKEN = "8876033736:AAH-EoESxq8aTDDMJE3gtxOC7hOZ2x0e5wg"  # توکن ربات خود را اینجا قرار دهید

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("ربات روشن شد!")
    app.run_polling()
