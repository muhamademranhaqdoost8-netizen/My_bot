import os
import glob
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

GET_LINK, GET_QUALITY = range(2)

dedef download_media(url: str, mode: str, quality: str) -> list:
    os.makedirs("downloads", exist_ok=True)
    if mode == "audio":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'max_filesize': 45 * 1024 * 1024,
            'quiet': True,
        }
    else:
        quality_map = {
            "360": "bestvideo[height<=360]+bestaudio/best[height<=360]/best",
            "480": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
            "720": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        }
        f_selector = quality_map.get(quality, "bestvideo+bestaudio/best")
        ydl_opts = {
            'format': f_selector,
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'max_filesize': 45 * 1024 * 1024,
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
        f"سلام **{user_name}** عزیز! 👋\n"
        "به ربات پیشرفته دانلودر خوش آمدید.\n\n"
        "✨ این ربات با افتخار توسط **عمران نوری** ساخته شده است.\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    keyboard = [
        [InlineKeyboardButton("📥 دانلود ویدیو از یوتیوب", callback_data="opt_yt_video")],
        [InlineKeyboardButton("🎵 دانلود آهنگ از یوتیوب", callback_data="opt_yt_audio")],
        [InlineKeyboardButton("📸 دانلود پست و استوری اینستاگرام", callback_data="opt_insta")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    return GET_LINK

async def menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    context.user_data['action_type'] = data
    
    if data == "opt_insta":
        context.user_data['quality'] = "best"
        context.user_data['mode'] = "video"
        await query.message.reply_text("🔗 لینک **پست یا استوری اینستاگرام** را ارسال کنید:")
        return GET_QUALITY
    else:
        await query.message.reply_text("🔗 لینک مد نظر از **یوتیوب** را ارسال کنید:")
        return GET_LINK

async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("⚠️ لطفاً یک لینک معتبر ارسال کنید:")
        return GET_LINK
        
    context.user_data['url'] = url
    action = context.user_data.get('action_type')
    
    if action == "opt_insta":
        return await process_download(update, context)
    
    keyboard = [
        [
            InlineKeyboardButton("360p", callback_data="q_360"),
            InlineKeyboardButton("480p", callback_data="q_480")
        ],
        [
            InlineKeyboardButton("720p", callback_data="q_720"),
            InlineKeyboardButton("1080p", callback_data="q_1080")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚙️ لطفاً کیفیت مورد نظر را انتخاب کنید:", reply_markup=reply_markup)
    return GET_QUALITY

async def receive_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    quality_data = query.data.replace("q_", "")
    context.user_data['quality'] = quality_data
    
    action = context.user_data.get('action_type')
    context.user_data['mode'] = "audio" if action == "opt_yt_audio" else "video"
    
    await query.message.edit_text("⏳ در حال پردازش و دانلود فایل...")
    return await execute_and_send(query.message, context)

async def execute_and_send(message, context):
    url = context.user_data.get('url')
    mode = context.user_data.get('mode')
    quality = context.user_data.get('quality', '720')
    
    files = []
    try:
        files = download_media(url, mode, quality)
        if files:
            await message.edit_text("⬆️ در حال ارسال به تلگرام...")
            for f in files:
                with open(f, 'rb') as media_file:
                    if f.endswith(('.jpg', '.png', '.jpeg', '.webp')):
                        await message.reply_photo(photo=media_file)
                    elif mode == "audio":
                        await message.reply_audio(audio=media_file)
                    else:
                        await message.reply_video(video=media_file)
            
            await message.reply_text(
                "✨ **تشکر از استفاده شما!**\nکار شما با موفقیت انجام شد.",
                parse_mode="Markdown"
            )
        else:
            await message.edit_text("❌ خطا: امکان دانلود فایل وجود نداشت.")
    except Exception as e:
        await message.edit_text(f"❌ خطا: {str(e)[:120]}")
    finally:
        for f in glob.glob("downloads/*"):
            if os.path.exists(f):
                os.remove(f)
    return ConversationHandler.END

async def process_download(update, context):
    status_msg = await update.message.reply_text("📥 در حال دانلود از اینستاگرام...")
    context.user_data['mode'] = "video"
    url = context.user_data.get('url')
    
    files = []
    try:
        files = download_media(url, "video", "best")
        if files:
            await status_msg.edit_text("⬆️ در حال ارسال...")
            for f in files:
                with open(f, 'rb') as media_file:
                    if f.endswith(('.jpg', '.png', '.jpeg', '.webp')):
                        await update.message.reply_photo(photo=media_file)
                    else:
                        await update.message.reply_video(video=media_file)
            
            await update.message.reply_text(
                "✨ **سپاس از اعتماد شما!** کار به اتمام رسید.",
                parse_mode="Markdown"
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ خطا در دریافت.")
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا: {str(e)[:100]}")
    finally:
        for f in glob.glob("downloads/*"):
            if os.path.exists(f):
                os.remove(f)
    return ConversationHandler.END

if __name__ == '__main__':
    BOT_TOKEN = "8876033736:AAH-EoESxq8aTDDMJE3gtxOC7hOZ2x0e5wg"  # توکن خود را اینجا بگذارید

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GET_LINK: [
                CallbackQueryHandler(menu_click, pattern="^opt_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)
            ],
            GET_QUALITY: [
                CallbackQueryHandler(receive_quality, pattern="^q_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    app.add_handler(conv_handler)
    print("ربات روشن شد!")
    app.run_polling()
