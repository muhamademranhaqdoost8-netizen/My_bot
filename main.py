import os
import glob
import static_ffmpeg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import yt_dlp

# اضافه کردن ffmpeg به مسیر سیستم به صورت خودکار
static_ffmpeg.add_paths()

GET_LINK = range(1)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"سلام **{user_name}** عزیز! 👋\n"
        "به ربات پیشرفته دانلودر خوش آمدید.\n\n"
        "✨ این ربات با افتخار توسط **عمران نوری** ساخته شده است.\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )def download_media(url: str, mode: str) -> list:
    os.makedirs("downloads", exist_ok=True)
    
    if mode == "audio":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'max_filesize': 48 * 1024 * 1024,
            'quiet': True,
        }
    else:
        # انتخاب منعطف: بهترین تصویر + بهترین صدا از هر نوع فرمتی
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',  # تبدیل خروجی نهایی به mp4 توسط ffmpeg
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'max_filesize': 48 * 1024 * 1024,
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

    keyboard = [
        [InlineKeyboardButton("📥 دانلود ویدیو از یوتیوب", callback_data="opt_yt_video")],
        [InlineKeyboardButton("🎵 دانلود آهنگ از یوتیوب", callback_data="opt_yt_audio")],
        [InlineKeyboardButton("📸 دانلود پست و استوری اینستاگرام", callback_data="opt_insta")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
        
    return GET_LINK

async def menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "opt_yt_audio":
        context.user_data['mode'] = "audio"
        await query.message.reply_text("🎵 لطفاً لینک **آهنگ/ویدیو از یوتیوب** را ارسال کنید:")
    elif data == "opt_yt_video":
        context.user_data['mode'] = "video"
        await query.message.reply_text("📥 لطفاً لینک **ویدیو از یوتیوب** را ارسال کنید:")
    elif data == "opt_insta":
        context.user_data['mode'] = "video"
        await query.message.reply_text("📸 لطفاً لینک **پست یا استوری اینستاگرام** را ارسال کنید:")
        
    return GET_LINK

async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("⚠️ لطفاً یک لینک معتبر (شروع با https) ارسال کنید.")
        return GET_LINK
        
    mode = context.user_data.get('mode', 'video')
    status_msg = await update.message.reply_text("⏳ در حال پردازش و دانلود... لطفاً کمی صبر کنید.")
    
    files = []
    try:
        files = download_media(url, mode)
        if files:
            await status_msg.edit_text("⬆️ در حال ارسال به تلگرام...")
            for f in files:
                with open(f, 'rb') as media_file:
                    if f.endswith(('.jpg', '.png', '.jpeg', '.webp')):
                        await update.message.reply_photo(photo=media_file)
                    elif mode == "audio" or f.endswith(('.mp3', '.m4a', '.aac', '.opus', '.wav', '.ogg')):
                        await update.message.reply_audio(audio=media_file)
                    else:
                        await update.message.reply_video(video=media_file)
            
            await update.message.reply_text(
                "✨ **دانلود با موفقیت انجام شد!**\nبرای دانلود بعدی روی گزینه‌های زیر بزنید:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 دانلود ویدیو از یوتیوب", callback_data="opt_yt_video")],
                    [InlineKeyboardButton("🎵 دانلود آهنگ از یوتیوب", callback_data="opt_yt_audio")],
                    [InlineKeyboardButton("📸 دانلود پست و استوری اینستاگرام", callback_data="opt_insta")]
                ]),
                parse_mode="Markdown"
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ خطا: فایلی یافت نشد یا قابل دانلود نبود.")
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در دانلود: {str(e)[:120]}")
    finally:
        for f in glob.glob("downloads/*"):
            if os.path.exists(f):
                os.remove(f)
                
    return GET_LINK

if __name__ == '__main__':
    BOT_TOKEN = "8876033736:AAH-EoESxq8aTDDMJE3gtxOC7hOZ2x0e5wg"  # توکن ربات خود را اینجا بگذارید

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(menu_click, pattern="^opt_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)
        ],
        states={
            GET_LINK: [
                CallbackQueryHandler(menu_click, pattern="^opt_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    
    app.add_handler(conv_handler)
    print("ربات روشن شد!")
    app.run_polling()
