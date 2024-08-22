import logging
import os
from pytube import YouTube
import instaloader
import spotipy
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# تنظیمات اولیه
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '6935623650:AAGbPzsciRx6tyFf489t-vnqLLyo7XnSpmI'
bot = telebot.TeleBot(TOKEN)

ADMIN_CHAT_ID = '1200237209'  # آیدی ادمین برای پشتیبانی

# تابع برای ارسال منوی اصلی
def send_main_menu(message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("یوتیوب", callback_data="youtube"),
        InlineKeyboardButton("اینستاگرام", callback_data="instagram"),
        InlineKeyboardButton("ساندکلاود", callback_data="soundcloud"),
        InlineKeyboardButton("اسپاتیفای", callback_data="spotify"),
        InlineKeyboardButton("پشتیبانی", callback_data="support")
    )
    bot.send_message(message.chat.id, "🎉 *خوش آمدید!*\nلطفاً یکی از گزینه‌ها را انتخاب کنید:", reply_markup=markup, parse_mode='Markdown')

# هندلر شروع ربات و نمایش منوی اصلی
@bot.message_handler(commands=['start'])
def start(message):
    send_main_menu(message)

# هندلر برای انتخاب پلتفرم
@bot.callback_query_handler(func=lambda call: call.data in ["youtube", "instagram", "soundcloud", "spotify", "support"])
def choose_platform(call):
    platform = call.data

    if platform == "youtube":
        bot.send_message(call.message.chat.id, "🔗 *لینک یوتیوب خود را ارسال کنید.*", parse_mode='Markdown')
        bot.register_next_step_handler(call.message, get_link, platform)
    elif platform == "support":
        bot.send_message(call.message.chat.id, "📩 *پیام خود را برای پشتیبانی ارسال کنید:*", parse_mode='Markdown')
        bot.register_next_step_handler(call.message, support_message)
    else:
        bot.send_message(call.message.chat.id, "🔗 *لینک پلتفرم مورد نظر را ارسال کنید.*", parse_mode='Markdown')
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

# تابع برای پردازش لینک یوتیوب و انتخاب کیفیت
def process_youtube_link(link, message):
    try:
        yt = YouTube(link)
        title = yt.title
        duration = yt.length

        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("فقط صدا (بالاترین کیفیت)", callback_data=f'youtube_audio_{yt.video_id}'),
            InlineKeyboardButton("144p", callback_data=f'youtube_144_{yt.video_id}'),
            InlineKeyboardButton("360p", callback_data=f'youtube_360_{yt.video_id}'),
            InlineKeyboardButton("720p", callback_data=f'youtube_720_{yt.video_id}'),
            InlineKeyboardButton("1080p", callback_data=f'youtube_1080_{yt.video_id}')
        )
        
        bot.send_message(message.chat.id, f"🎬 *عنوان:* {title}\n⏱ *مدت زمان:* {duration // 60} دقیقه {duration % 60} ثانیه\n\n*لطفاً کیفیت دلخواه خود را انتخاب کنید:*", reply_markup=markup, parse_mode='Markdown')

    except Exception as e:
        bot.send_message(message.chat.id, "❌ خطایی در پردازش لینک یوتیوب رخ داد.")

# هندلر برای دانلود ویدئو از یوتیوب و حذف دکمه‌ها پس از انتخاب
@bot.callback_query_handler(func=lambda call: call.data.startswith('youtube'))
def youtube_download(call):
    format_id = call.data.split('_')[1]
    video_id = call.data.split('_')[2]

    yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")

    # حذف دکمه‌ها پس از انتخاب
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    progress_message = bot.send_message(call.message.chat.id, "📥 *در حال دانلود، لطفا صبر کنید...*", parse_mode='Markdown')

    if format_id == 'audio':
        stream = yt.streams.filter(only_audio=True).first()
    else:
        stream = yt.streams.filter(res=format_id, progressive=True).first()

    if not stream:
        bot.send_message(call.message.chat.id, "❌ فرمت انتخاب شده موجود نیست.")
        return

    # دانلود و ارسال فایل
    try:
        file_path = stream.download()
        bot.send_message(call.message.chat.id, "✅ دانلود کامل شد، ارسال فایل...", parse_mode='Markdown')
        bot.send_document(call.message.chat.id, open(file_path, 'rb'))
        os.remove(file_path)
    except Exception as e:
        bot.send_message(call.message.chat.id, "❌ خطایی در دانلود ویدئو رخ داد.")

# تابع پشتیبانی
def support_message(message):
    user = message.from_user
    bot.send_message(ADMIN_CHAT_ID, f"پیام جدید از {user.username} ({user.id}):\n\n{message.text}")
    bot.send_message(message.chat.id, "پیام شما برای پشتیبانی ارسال شد. به زودی پاسخ دریافت خواهید کرد.")

# پاسخ ادمین به پیام پشتیبانی
@bot.message_handler(func=lambda message: message.chat.id == ADMIN_CHAT_ID)
def reply_support(message):
    if message.reply_to_message:
        user_id = message.reply_to_message.text.split("(")[-1].split(")")[0]
        response = message.text
        bot.send_message(user_id, f"پاسخ پشتیبانی:\n\n{response}")
    else:
        bot.send_message(ADMIN_CHAT_ID, "لطفاً به پیام کاربر پاسخ دهید تا پاسخ شما ارسال شود.")

# تابع دانلود از اینستاگرام
def download_instagram(link, message):
    loader = instaloader.Instaloader()
    post = instaloader.Post.from_shortcode(loader.context, link.split("/")[-2])
    loader.download_post(post, target='.')
    
    file_name = f"{post.shortcode}.mp4" if post.is_video else f"{post.shortcode}.jpg"
    bot.send_message(message.chat.id, "📥 در حال ارسال فایل...")
    bot.send_document(message.chat.id, open(file_name, 'rb'))
    os.remove(file_name)

# تابع دانلود از اسپاتیفای
def download_spotify(link, message):
    sp = spotipy.Spotify(auth='YOUR_SPOTIFY_TOKEN')
    track = sp.track(link)
    bot.send_message(message.chat.id, f"لینک اسپاتیفای: {track['external_urls']['spotify']}")

# اجرای ربات
if __name__ == '__main__':
    bot.polling(none_stop=True)
