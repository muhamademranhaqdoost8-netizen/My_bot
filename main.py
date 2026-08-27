import os
import glob
import requests
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

GET_LINK = range(1)

def download_media(url: str, mode: str) -> list:
    os.makedirs("downloads", exist_ok=True)
    out_file = "downloads/downloaded_media.mp4" if mode == "video" else "downloads/downloaded_media.mp3"

    # ارسال مستقیم درخواست به سرورهای واسط دانلود بدون مسدودسازی
    api_endpoint = "https://co.wuk.sh/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {
        "url": url,
        "downloadMode": "audio" if mode == "audio" else "auto"
    }

    response = requests.post(api_endpoint, json=payload, headers=headers, timeout=25)
    data = response.json()
    
    stream_url = data.get("url")
    if stream_url:
        with requests.get(stream_url, stream=True, timeout=90) as r:
            r.raise_for_status()
            with open(out_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=16384):
                    if chunk:
                        f.write(chunk)
        return [out_file]
    
    return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"سلام **{user_name}** عزیز! 👋\n"
        "به ربات دانلودر خوش آمدید.\n\n"
        "✨ طراحی و اجرا توسط: **عمران نوری**\n\n"
        "لطفاً نوع دانلود را انتخاب کنید:"
    )
    keyboard = [
        [InlineKeyboardButton("📥 دانلود ویدیو از یوتیوب", callback_data="opt_yt_video")],
        [InlineKeyboardButton("🎵 دانلود آهنگ از یوتیوب", callback_data="opt_yt_audio")],
        [InlineKeyboardButton("📸 دانلود از اینستاگرام", callback_data="opt_insta")]
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
        await query.message.reply_text("🎵 لطفاً لینک آهنگ/ویدیو از یوتیوب را ارسال کنید:")
    elif data == "opt_yt_video":
        context.user_data['mode'] = "video"
        await query.message.reply_text("📥 لطفاً لینک ویدیو از یوتیوب را ارسال کنید:")
    elif data == "opt_insta":
        context.user_data['mode'] = "video"
        await query.message.reply_text("📸 لطفاً لینک پست یا ریلز اینستاگرام را ارسال کنید:")
        
    return GET_LINK

async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("⚠️ لطفاً یک لینک معتبر ارسال کنید.")
        return GET_LINK
        
    mode = context.user_data.get('mode', 'video')
    status_msg = await update.message.reply_text("⏳ در حال دانلود و دریافت مستقیم فایل... لطفاً صبر کنید.")
    
    try:
        files = download_media(url, mode)
        if files:
            await status_msg.edit_text("⬆️ در حال آپلود روی تلگرام...")
            for f in files:
                with open(f, 'rb') as media_file:
                    if mode == "audio":
                        await update.message.reply_audio(audio=media_file)
                    else:
                        await update.message.reply_video(video=media_file)
            
            await update.message.reply_text(
                "✨ **دانلود با موفقیت انجام شد!**\nگزینه بعدی را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 دانلود ویدیو از یوتیوب", callback_data="opt_yt_video")],
                    [InlineKeyboardButton("🎵 دانلود آهنگ از یوتیوب", callback_data="opt_yt_audio")],
                    [InlineKeyboardButton("📸 دانلود از اینستاگرام", callback_data="opt_insta")]
                ]),
                parse_mode="Markdown"
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ خطا: دریافت لینک از این آدرس ممکن نبود.")
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا: {str(e)[:120]}")
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
