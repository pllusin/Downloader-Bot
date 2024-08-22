import logging
import os
import yt_dlp
import instaloader
import spotipy
import soundcloud
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler

# تنظیمات اولیه برای ورود به API تلگرام
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# مراحل گفتگو
CHOOSE_PLATFORM, GET_LINK, CHOOSE_QUALITY = range(3)

# توکن ربات تلگرام و آیدی ادمین
TOKEN = '6935623650:AAGbPzsciRx6tyFf489t-vnqLLyo7XnSpmI'
ADMIN_ID = 123456789  # جایگزین با آیدی ادمین

# هندلر برای شروع ربات
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "سلام! لطفاً یکی از پلتفرم‌ها را برای دانلود انتخاب کنید:\n\n"
        "1️⃣ یوتیوب\n"
        "2️⃣ اینستاگرام\n"
        "3️⃣ ساندکلاود\n"
        "4️⃣ اسپاتیفای",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("یوتیوب", callback_data='youtube')],
            [InlineKeyboardButton("اینستاگرام", callback_data='instagram')],
            [InlineKeyboardButton("ساندکلاود", callback_data='soundcloud')],
            [InlineKeyboardButton("اسپاتیفای", callback_data='spotify')]
        ])
    )
    return CHOOSE_PLATFORM

# هندلر برای دریافت پلتفرم انتخاب شده
async def choose_platform(update: Update, context: CallbackContext):
    query = update.callback_query
    platform = query.data
    context.user_data['platform'] = platform
    await query.message.edit_text(
        "لطفاً لینک مربوط به این پلتفرم را ارسال کنید."
    )
    return GET_LINK

# هندلر برای دریافت لینک و دانلود
async def get_link(update: Update, context: CallbackContext):
    link = update.message.text
    platform = context.user_data.get('platform')

    try:
        if platform == 'youtube':
            await handle_youtube(link, update)
        elif platform == 'instagram':
            await download_instagram(link, update)
        elif platform == 'soundcloud':
            await download_soundcloud(link, update)
        elif platform == 'spotify':
            await download_spotify(link, update)
    except Exception as e:
        await update.message.reply_text(f"⚠️ خطا در دانلود: {e}")

    return ConversationHandler.END

# تابع دانلود ویدیو از یوتیوب
async def handle_youtube(link, update):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(link, download=False)
        title = info_dict.get('title', 'بدون عنوان')
        duration = info_dict.get('duration', 'ناشناخته')
        formats = info_dict.get('formats', [])
        
        keyboard = []
        for fmt in formats:
            quality = fmt.get('format_note', 'کیفیت نامشخص')
            file_size = fmt.get('filesize', 0)
            button_text = f"{quality} ({file_size // (1024 * 1024)} MB)"
            callback_data = f"{fmt['format_id']}|{link}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        if not keyboard:
            await update.message.reply_text("⚠️ هیچ کیفیتی برای دانلود پیدا نشد.")
            return
        
        keyboard.append([InlineKeyboardButton("لغو", callback_data='cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📹 عنوان: {title}\n⏳ مدت زمان: {duration} ثانیه\n\n"
            "لطفاً کیفیت مورد نظر را انتخاب کنید:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return CHOOSE_QUALITY

# هندلر برای انتخاب کیفیت یوتیوب
async def choose_quality(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('|')
    format_id, link = data
    ydl_opts = {
        'format': format_id,
        'outtmpl': '%(title)s.%(ext)s'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(link, download=True)
        file_name = ydl.prepare_filename(info_dict)
        await query.message.reply_document(document=open(file_name, 'rb'))
        os.remove(file_name)
    return ConversationHandler.END

# تابع دانلود از اینستاگرام
async def download_instagram(link, update):
    loader = instaloader.Instaloader()
    post = instaloader.Post.from_shortcode(loader.context, link.split("/")[-2])
    loader.download_post(post, target='.')
    file_name = f"{post.shortcode}.mp4" if post.is_video else f"{post.shortcode}.jpg"
    await update.message.reply_document(document=open(file_name, 'rb'))
    os.remove(file_name)

# تابع دانلود از ساندکلاود
async def download_soundcloud(link, update):
    client = soundcloud.Client(client_id='YOUR_SOUNDCLOUD_CLIENT_ID')
    track = client.get('/resolve', url=link)
    stream_url = client.get(track.stream_url, allow_redirects=False)
    response = requests.get(stream_url.location, stream=True)
    with open(f"{track.title}.mp3", 'wb') as f:
        f.write(response.content)
    await update.message.reply_document(document=open(f"{track.title}.mp3", 'rb'))
    os.remove(f"{track.title}.mp3")

# تابع دانلود از اسپاتیفای
async def download_spotify(link, update):
    sp = spotipy.Spotify(auth='YOUR_SPOTIFY_TOKEN')
    track = sp.track(link)
    await update.message.reply_text(f"🔗 لینک اسپاتیفای: {track['external_urls']['spotify']}")

# تابع برای ارسال پیام‌های پشتیبانی به ادمین
async def support(update: Update, context: CallbackContext):
    if update.message.from_user.id == ADMIN_ID:
        if update.message.reply_to_message:
            user_message = update.message.reply_to_message.text
            response_message = update.message.text
            user_id = update.message.reply_to_message.from_user.id
            await context.bot.send_message(user_id, f"👨‍💼 پاسخ ادمین:\n\n{response_message}")
            await update.message.reply_text("✅ پاسخ شما ارسال شد.")
        else:
            await update.message.reply_text("❌ لطفاً به پیامی که می‌خواهید پاسخ دهید، پاسخ دهید.")
    else:
        await update.message.reply_text("❌ شما مجاز به ارسال پاسخ نیستید.")

# تابع برای پشتیبانی از سیستم
async def support_start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "برای پشتیبانی، لطفاً سوال یا مشکلتان را ارسال کنید و ادمین به شما پاسخ خواهد داد. "
        "سوالات شما به ادمین ارسال می‌شود."
    )

async def handle_support_message(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        await context.bot.send_message(ADMIN_ID, f"📬 پیام جدید از {update.message.from_user.full_name}:\n\n{update.message.text}")
        await update.message.reply_text("✅ پیام شما به ادمین ارسال شد. در اسرع وقت پاسخ خواهیم داد.")
    else:
        await support(update, context)

# هندلر برای لغو گفتگو
async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text('❌ دانلود لغو شد.')
    return ConversationHandler.END

# تابع اصلی اجرای ربات
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('support', support_start)],
        states={
            CHOOSE_PLATFORM: [CallbackQueryHandler(choose_platform)],
            GET_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)],
            CHOOSE_QUALITY: [CallbackQueryHandler(choose_quality)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support_message))
    application.run_polling()

if __name__ == '__main__':
    main()