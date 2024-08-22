import logging
import os
import yt_dlp
import instaloader
import spotipy
import telebot

# تنظیمات اولیه برای لاگ‌ها
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# توکن ربات تلگرام
TOKEN = '6935623650:AAGbPzsciRx6tyFf489t-vnqLLyo7XnSpmI'
bot = telebot.TeleBot(TOKEN)

# تابع برای ارسال پیام وضعیت و به‌روزرسانی آن
def update_status_message(message, progress_message, current_progress, total_progress):
    try:
        progress_percent = (current_progress / total_progress) * 100
        text = f"📥 *در حال دانلود، لطفا صبر کنید...*\n\n⏳ پیشرفت: {progress_percent:.2f}%"
        bot.edit_message_text(chat_id=message.chat.id, message_id=progress_message.message_id, text=text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"خطا در آپدیت پیام وضعیت: {e}")

# هندلر برای شروع ربات و انتخاب پلتفرم
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        telebot.types.InlineKeyboardButton("یوتیوب", callback_data="youtube"),
        telebot.types.InlineKeyboardButton("اینستاگرام", callback_data="instagram"),
        telebot.types.InlineKeyboardButton("ساندکلاود", callback_data="soundcloud"),
        telebot.types.InlineKeyboardButton("اسپاتیفای", callback_data="spotify")
    )
    bot.send_message(message.chat.id, "🎉 *خوش آمدید!*\nلطفاً یکی از پلتفرم‌ها را انتخاب کنید:", reply_markup=markup, parse_mode='Markdown')

# هندلر برای انتخاب پلتفرم
@bot.callback_query_handler(func=lambda call: True)
def choose_platform(call):
    platform = call.data
    bot.send_message(call.message.chat.id, "🔗 *لینک مربوط به این پلتفرم را ارسال کنید.*", parse_mode='Markdown')
    bot.register_next_step_handler(call.message, get_link, platform)

# هندلر برای دریافت لینک و پردازش آن
def get_link(message, platform):
    link = message.text
    if platform == 'youtube':
        process_youtube_link(link, message)
    elif platform == 'instagram':
        download_instagram(link, message)
    elif platform == 'spotify':
        download_spotify(link, message)
    # در صورت وجود ساندکلاود می‌توانید این بخش را اضافه کنید.

# تابع برای پردازش لینک یوتیوب و انتخاب کیفیت
def process_youtube_link(link, message):
    ydl_opts = {'format': 'best', 'noplaylist': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(link, download=False)
        title = info_dict.get('title', 'ویدئو')
        duration = info_dict.get('duration', 0)
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            telebot.types.InlineKeyboardButton("صدا فقط (بالا‌ترین کیفیت)", callback_data=f'youtube_audio_{info_dict["id"]}'),
            telebot.types.InlineKeyboardButton("144p", callback_data=f'youtube_144_{info_dict["id"]}'),
            telebot.types.InlineKeyboardButton("360p", callback_data=f'youtube_360_{info_dict["id"]}'),
            telebot.types.InlineKeyboardButton("720p", callback_data=f'youtube_720_{info_dict["id"]}'),
            telebot.types.InlineKeyboardButton("1080p", callback_data=f'youtube_1080_{info_dict["id"]}')
        )
        
        bot.send_message(message.chat.id, f"🎬 *عنوان:* {title}\n⏱ *مدت زمان:* {duration // 60} دقیقه {duration % 60} ثانیه\n\n*لطفاً کیفیت دلخواه خود را انتخاب کنید:*", reply_markup=markup, parse_mode='Markdown')

# تابع برای دانلود ویدئو از یوتیوب و به‌روزرسانی وضعیت دانلود
@bot.callback_query_handler(func=lambda call: call.data.startswith('youtube'))
def youtube_download(call):
    format_id = call.data.split('_')[1]
    info_dict_id = call.data.split('_')[2]

    # بازسازی اطلاعات ویدئو با استفاده از id
    ydl_opts = {
        'format': format_id if format_id != 'audio' else 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s'
    }

    # پیام در حال دانلود
    progress_message = bot.send_message(call.message.chat.id, "📥 *در حال دانلود، لطفا صبر کنید...*", parse_mode='Markdown')

    def progress_hook(d):
        if d['status'] == 'downloading':
            update_status_message(call.message, progress_message, d['downloaded_bytes'], d['total_bytes'])

    ydl_opts['progress_hooks'] = [progress_hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(info_dict_id, download=False)
        ydl.download([info_dict['webpage_url']])
        file_name = ydl.prepare_filename(info_dict)
        
        # ارسال فایل دانلود شده به کاربر
        with open(file_name, 'rb') as f:
            bot.send_document(call.message.chat.id, f)
        
        # حذف فایل پس از ارسال
        os.remove(file_name)

# تابع دانلود از اینستاگرام
def download_instagram(link, message):
    loader = instaloader.Instaloader()
    post = instaloader.Post.from_shortcode(loader.context, link.split("/")[-2])
    loader.download_post(post, target='.')
    
    file_name = f"{post.shortcode}.mp4" if post.is_video else f"{post.shortcode}.jpg"
    progress_message = bot.send_message(message.chat.id, "📥 *در حال دانلود، لطفا صبر کنید...*", parse_mode='Markdown')

    # ارسال فایل دانلود شده به کاربر
    with open(file_name, 'rb') as f:
        bot.send_document(message.chat.id, f)
    
    os.remove(file_name)

# تابع دانلود از اسپاتیفای
def download_spotify(link, message):
    sp = spotipy.Spotify(auth='YOUR_SPOTIFY_TOKEN')
    track = sp.track(link)
    bot.send_message(message.chat.id, f"لینک اسپاتیفای: {track['external_urls']['spotify']}")

# اجرای ربات
if __name__ == '__main__':
    bot.polling(none_stop=True)
