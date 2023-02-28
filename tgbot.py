import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import openai
import pymysql
import time

# Telegram
token = 'Ваш токен бота'
bot = telebot.TeleBot(token)

# ChatGPT
openai.api_key = "Ваш API-key ChatGPT"
openai.Model.list()

def get_chatgpt_response(prompt):
    return openai.Completion.create(
        model='text-davinci-003',
        prompt=prompt,
        temperature=0.5,
        max_tokens=2048,
        top_p=0.7,
        frequency_penalty=0,
    )['choices'][0]['text']

#MySQL
connection = pymysql.connect(host='localhost',
                             user='root',
                             password='',
                             database='chatgpt_bot',
                             cursorclass=pymysql.cursors.DictCursor)

def check_account(id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM `accounts` WHERE `id` = %s", id)
        account_data = cursor.fetchone()
        if account_data == None:
            cursor.execute("INSERT INTO `accounts` (`id`, `queries`, `time`, `promocode`) VALUES (%s, %s, %s, %s)", (id, 0, time.time(), 'NULL'))
    connection.commit()

def get_reply(message):
    prompt = message.text
    limit = False
    response = ''
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM `accounts` WHERE `id` = '{message.from_user.id}'")
        account_data = cursor.fetchone()
        if account_data['time'] >= int(time.time()):
            if account_data['promocode'] == True:
                if account_data['queries'] <= 15:
                    response = get_chatgpt_response(prompt)
                    cursor.execute("UPDATE `accounts` SET `queries`=%s", account_data['queries'] + 1)
                else:
                    limit = True
                    response = 'Вы превысили лимит запросов. До снятия лимита осталось: ' + str(int((account_data['time'] - int(time.time()))/60)) + 'минут\nДля снятия лимита используйте промокод, узнав его у админа'
            else:
                response = get_chatgpt_response(prompt)
        else:
            response = get_chatgpt_response(prompt)
            cursor.execute("UPDATE `accounts` SET `id`=%s,`queries`=%s,`time`=%s", (message.from_user.id, 1, int(time.time()) + 3600))
    connection.commit()
    return response, limit

@bot.message_handler(commands=['start'])
def start_message(message):
    check_account(message.from_user.id)
    bot.send_message(message.from_user.id,f'Добро пожаловать, {message.from_user.first_name}!\nДля того, чтобы помотреть свой аккаунт введите /account')

@bot.message_handler(commands=['admin'])
def start_message(message):
    check_account(message.from_user.id)
    if message.from_user.id == useridtelegram:
        admin_command = message.text.replace('/admin ', '')
        if admin_command.split(' ')[0].lower() == 'промокод':
            promocode_name = admin_command.split(' ')[1]
            promocode_time = admin_command.split(' ')[2]
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO `promocodes` (`promocode`, `time`) VALUES (%s, %s);", (promocode_name, promocode_time))
            connection.commit()
        else:
            bot.reply_to(message, 'Чтобы создать промокод напишите:\n/admin промокод <название промокода> <время действия промокода в секундах>')
    else:
        bot.reply_to(message, 'Вы не можете использовать эту команду, так как у вас не достаточно прав')

@bot.message_handler(commands=['account'])
def start_message(message):
    check_account(message.from_user.id)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM `accounts` WHERE `id` = '{message.from_user.id}'")
        account_data = cursor.fetchone()
        if account_data['time'] < int(time.time()):
            queries = 0
        else:
            queries = account_data['queries']
        if account_data['promocode'] == None:
            markup = InlineKeyboardMarkup()
            button1 = InlineKeyboardButton('Купить промокод', url='t.me/pauciloquente')
            markup.add(button1)
            bot.reply_to(message, f'Ваш ID: {message.from_user.id}\nЗапросов за этот час: {queries}\n\nУ вас нет промокода. Хотите пользоваться ботом без ограничений? Купите подписку', reply_markup=markup)
        else:
            markup = InlineKeyboardMarkup()
            button1 = InlineKeyboardButton('Написать админу', url='t.me/pauciloquente')
            markup.add(button1)
            promocode_time = int((account_data['time'] - time.time())/60)
            bot.reply_to(message, f'Ваш ID: {message.from_user.id}\n\nВаш промокод: ' + account_data['promocode'] + '\nОсталось минут до окончания действия промокода: ' + str(promocode_time), reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def bot_response(message):
    check_account(message.from_user.id)
    if message.text.split(' ')[0].lower() == 'промокод':
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM `promocodes` WHERE `promocode` = %s", message.text.split(' ')[1])
            promocode_data = cursor.fetchone()
            if promocode_data != None:
                cursor.execute("UPDATE `accounts` SET `promocode`=%s, `time`=%s", (message.text.split(' ')[1], int(time.time() + promocode_data['time'])))
            else:
                markup = InlineKeyboardMarkup()
                button1 = InlineKeyboardButton('Купить подписку', url='t.me/pauciloquente')
                markup.add(button1)
                bot.reply_to(message, 'Нет такого промокода? Хотите преобрести промокод? Пишите админу', reply_markup=markup)
        connection.commit()
    else:
        response, limit = get_reply(message)
        if limit == False:
            bot.reply_to(message, response)
        else:
            markup = InlineKeyboardMarkup()
            button1 = InlineKeyboardButton('Купить подписку', url='t.me/pauciloquente')
            markup.add(button1)
            bot.reply_to(message, response, reply_markup=markup)

bot.infinity_polling()
connection.close()
