import logging
import os
import yt_dlp
import instaloader
import spotipy
# import soundcloud
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler

# تنظیمات اولیه برای ورود به API تلگرام
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# مراحل گفتگو
CHOOSE_PLATFORM, GET_LINK, CHOOSE_QUALITY = range(3)

# توکن ربات تلگرام
TOKEN = 'YOUR_BOT_TOKEN_HERE'
ADMIN_CHAT_ID = 'YOUR_ADMIN_CHAT_ID'

# هندلر برای شروع ربات
async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("یوتیوب", callback_data='youtube')],
        [InlineKeyboardButton("اینستاگرام", callback_data='instagram')],
        [InlineKeyboardButton("ساندکلاود", callback_data='soundcloud')],
        [InlineKeyboardButton("اسپاتیفای", callback_data='spotify')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("🎉 *خوش آمدید!*\nلطفاً یکی از پلتفرم‌ها را انتخاب کنید:", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    return CHOOSE_PLATFORM

# هندلر برای دریافت پلتفرم انتخاب شده
async def choose_platform(update: Update, context: CallbackContext):
    query = update.callback_query
    platform = query.data
    context.user_data['platform'] = platform
    await query.message.edit_text("🔗 *لینک مربوط به این پلتفرم را ارسال کنید.*", parse_mode=ParseMode.MARKDOWN)
    return GET_LINK

# هندلر برای دریافت لینک و پردازش آن
async def get_link(update: Update, context: CallbackContext):
    link = update.message.text
    platform = context.user_data.get('platform')

    if platform == 'youtube':
        await process_youtube_link(link, update, context)
    elif platform == 'instagram':
        await download_instagram(link, update)
    # elif platform == 'soundcloud':
    #     await download_soundcloud(link, update)
    elif platform == 'spotify':
        await download_spotify(link, update)

    return ConversationHandler.END

# تابع پردازش لینک یوتیوب و انتخاب کیفیت
async def process_youtube_link(link, update, context):
    ydl_opts = {
        'format': 'best',
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(link, download=False)
        title = info_dict.get('title', 'ویدئو')
        duration = info_dict.get('duration', 0)
        formats = info_dict.get('formats', [])
        
        # ساخت دکمه‌های شیشه‌ای برای انتخاب کیفیت
        keyboard = []
        for f in formats:
            format_id = f['format_id']
            resolution = f.get('resolution', 'نامشخص')
            filesize = f.get('filesize', 0)
            filesize_mb = round(filesize / (1024 * 1024), 2) if filesize else 'نامشخص'
            button_text = f"{resolution} - {filesize_mb} MB"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'quality_{format_id}')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)

        details_text = f"""
        🎬 *عنوان:* {title}
        ⏱ *مدت زمان:* {duration // 60} دقیقه {duration % 60} ثانیه
        
        *لطفاً کیفیت دلخواه خود را انتخاب کنید:*
        """
        await update.message.reply_text(details_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        context.user_data['info_dict'] = info_dict

# تابع برای دانلود ویدئوی یوتیوب با کیفیت انتخاب شده
async def youtube_download(update: Update, context: CallbackContext):
    query = update.callback_query
    format_id = query.data.split('_')[1]  # استخراج format_id
    info_dict = context.user_data['info_dict']
    
    ydl_opts = {
        'format': format_id,
        'outtmpl': '%(title)s.%(ext)s',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([info_dict['webpage_url']])
        file_name = ydl.prepare_filename(info_dict)
        await query.message.reply_document(document=open(file_name, 'rb'))
        os.remove(file_name)

# تابع دانلود از اینستاگرام
async def download_instagram(link, update):
    loader = instaloader.Instaloader()
    post = instaloader.Post.from_shortcode(loader.context, link.split("/")[-2])
    loader.download_post(post, target='.')
    file_name = f"{post.shortcode}.mp4" if post.is_video else f"{post.shortcode}.jpg"
    await update.message.reply_document(document=open(file_name, 'rb'))
    os.remove(file_name)

# تابع دانلود از ساندکلاود
# async def download_soundcloud(link, update):
#     client = soundcloud.Client(client_id='YOUR_SOUNDCLOUD_CLIENT_ID')
#     track = client.get('/resolve', url=link)
#     stream_url = client.get(track.stream_url, allow_redirects=False)
#     response = requests.get(stream_url.location, stream=True)
#     with open(f"{track.title}.mp3", 'wb') as f:
#         f.write(response.content)
#     await update.message.reply_document(document=open(f"{track.title}.mp3", 'rb'))
#     os.remove(f"{track.title}.mp3")

# تابع دانلود از اسپاتیفای
async def download_spotify(link, update):
    sp = spotipy.Spotify(auth='YOUR_SPOTIFY_TOKEN')
    track = sp.track(link)
    await update.message.reply_text(f"لینک اسپاتیفای: {track['external_urls']['spotify']}")

# سیستم پشتیبانی
async def support(update: Update, context: CallbackContext):
    await update.message.reply_text("📩 *پیام خود را ارسال کنید. پشتیبانی به زودی پاسخ خواهد داد.*", parse_mode=ParseMode.MARKDOWN)

async def receive_support_message(update: Update, context: CallbackContext):
    message = update.message.text
    user = update.message.from_user
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"پیام جدید از {user.username} ({user.id}):\n\n{message}")

async def reply_support(update: Update, context: CallbackContext):
    if update.message.reply_to_message:
        original_message = update.message.reply_to_message.text
        user_id = original_message.split("(")[-1].split(")")[0]
        response = update.message.text
        await context.bot.send_message(chat_id=user_id, text=f"پاسخ پشتیبانی:\n\n{response}")
    else:
        await update.message.reply_text("لطفاً به پیام کاربر پاسخ دهید تا پاسخ شما ارسال شود.")

# هندلر برای لغو گفتگو
async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text('❌ *دانلود لغو شد.*', parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

# تابع اصلی اجرای ربات
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSE_PLATFORM: [CallbackQueryHandler(choose_platform)],
            GET_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)],
            CHOOSE_QUALITY: [CallbackQueryHandler(youtube_download)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('support', support))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_support_message, block=False))
    application.add_handler(MessageHandler(filters.REPLY, reply_support, block=False))
    
    application.run_polling()

if __name__ == '__main__':
    main()
