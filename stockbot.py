#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
This Bot uses the Updater class to handle the bot.

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Job
import logging
import requests
import datetime
import json
import os
from os.path import join, dirname
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
last_price_korbit = {'btc_krw': 0, 'eth_krw': 0, 'xrp_krw': 0}
last_price_coinone = {'btc': 0, 'eth': 0, 'xrp': 0}
last_price_bitfinex = {'btcusd': 0, 'ethusd': 0, 'xrpusd': 0}


def save_lastprice():
    lastprice = [
        last_price_korbit,
        last_price_coinone,
        last_price_bitfinex,
        chat_ids
    ]
    with open('last_price.json', 'w') as data_file:
        json.dump(lastprice, data_file)


def load_lastprice(updater):
    global last_price_korbit, last_price_coinone, last_price_bitfinex, chat_ids

    try:
        with open('last_price.json') as data_file:
            lastprice = json.load(data_file)
        last_price_korbit = lastprice[0]
        last_price_coinone = lastprice[1]
        last_price_bitfinex = lastprice[2]
        chat_ids = lastprice[3]
    except:
        pass

    updater.job_queue.run_repeating(callback_alarm, 30, first=True)


coinname_korbit = {'btc_krw':'코빗 비트코인', 'eth_krw':'코빗 이더리움', 'xrp_krw':'코빗 리플   '}
coinname_coinone = {'btc':'코인원 비트코인', 'eth':'코인원 이더리움', 'xrp':'코인원 리플   '}
coinname_bitfinex = {'btcusd':'Bitfinex 비트코인', 'ethusd':'Bitfinex 이더리움', 'xrpusd':'Bitfinex 리플   '}
chat_ids = []

coin_sensitivity = {'btc_krw': 0.02, 'btc': 0.02, 'btcusd': 0.02,
                    'eth_krw': 0.02, 'eth': 0.02, 'ethusd': 0.02,
                    'xrp_krw': 0.04, 'xrp': 0.04, 'xrpusd': 0.04}

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    update.message.reply_text('Hi!')


def help(bot, update):
    update.message.reply_text('Help!')


def echo(bot, update):
    update.message.reply_text(update.message.text)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def get_korbit_current():
    coins = ['btc_krw', 'eth_krw', 'xrp_krw']
    current_price = {}
    msg = ""
    for coin in coins:
        ret = requests.get('https://api.korbit.co.kr/v1/ticker?currency_pair='+coin)
        r = json.loads(ret.text)
        value = int(r['last'])
        current_price[coin] = value
    return current_price 

def get_coinone_current():
    coins = ['btc', 'eth', 'xrp']
    current_price = {}
    msg = ""
    for coin in coins:
        ret = requests.get('https://api.coinone.co.kr/ticker/?currency='+coin)
        r = json.loads(ret.text)
        value = int(r['last'])
        current_price[coin] = value
    return current_price 

def get_bitfinex_current():
    coins = ['btcusd', 'ethusd', 'xrpusd']
    current_price = {}
    msg = ""
    for coin in coins:
        ret = requests.get('https://api.bitfinex.com/v1/pubticker/'+coin)
        r = json.loads(ret.text)
        value = float(r['last_price'])
        current_price[coin] = value
    return current_price

def make_msg(current_price_bitfinex, current_price_korbit, current_price_coinone, alarm_coin=""):
    global last_price_korbit, last_price_coinone, last_price_bitfinex
    msg = ''
    for coin in sorted(current_price_bitfinex):
        value = current_price_bitfinex[coin]
        star = "*" if coin == alarm_coin else ''
        msg = msg + "\n`{} ${:>10,.4f}({:+.4f}){}`".format(coinname_bitfinex[coin], value, value-last_price_bitfinex[coin], star)
    msg = msg + '\n'
    for coin in sorted(current_price_coinone):
        value = current_price_coinone[coin]
        star = "*" if coin == alarm_coin else ''
        msg = msg + "\n`{} {:>10,d}원({:+d}){}`".format(coinname_coinone[coin], value, value-last_price_coinone[coin], star)
    msg = msg + '\n'
    for coin in sorted(current_price_korbit):
        value = current_price_korbit[coin]
        star = "*" if coin == alarm_coin else ''
        msg = msg + "\n`{} {:>10,d}원({:+d}){}`".format(coinname_korbit[coin], value, value-last_price_korbit[coin], star)
    if current_price_bitfinex: last_price_bitfinex = current_price_bitfinex
    if current_price_coinone: last_price_coinone = current_price_coinone
    if current_price_korbit: last_price_korbit = current_price_korbit
    save_lastprice()
    return msg

def current_price(bot, update):
    current_price_coinone = get_coinone_current()
    current_price_korbit = get_korbit_current()
    current_price_bitfinex = get_bitfinex_current()
    update.message.reply_text(make_msg(current_price_bitfinex, current_price_korbit, current_price_coinone), parse_mode='Markdown')

def callback_alarm(bot, job):
    # check last and current
    try:
        current_price_coinone = get_coinone_current()
    except:
        current_price_coinone = {} 
    try:
        current_price_korbit = get_korbit_current()
    except:
        current_price_korbit = {} 
    try:
        current_price_bitfinex = get_bitfinex_current()
    except:
        current_price_bitfinex = {} 
    # send or not
    check = False
    for coin in current_price_bitfinex:
        value = current_price_bitfinex[coin]
        if value > last_price_bitfinex[coin] * (1.0 + coin_sensitivity[coin]) or value < last_price_bitfinex[coin] * (1.0 - coin_sensitivity[coin]):
            check = True
            alarm_coin = coin
    for coin in current_price_coinone:
        value = current_price_coinone[coin]
        if value > last_price_coinone[coin] * (1.0 + coin_sensitivity[coin]) or value < last_price_coinone[coin] * (1.0 - coin_sensitivity[coin]):
            check = True
            alarm_coin = coin
    for coin in current_price_korbit:
        value = current_price_korbit[coin]
        if value > last_price_korbit[coin] * (1.0 + coin_sensitivity[coin]) or value < last_price_korbit[coin] * (1.0 - coin_sensitivity[coin]):
            check = True
            alarm_coin = coin
    if check:
        msg = make_msg(current_price_bitfinex, current_price_korbit, current_price_coinone, alarm_coin)
        for chat_id in chat_ids:
            bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')

def callback_timer(bot, update, job_queue):
    global chat_ids
    bot.send_message(chat_id=update.message.chat_id,
                     text='시세알람 타이머 동작')
    chat_ids.append(update.message.chat_id)
    save_lastprice()

def main():
    # Create the EventHandler and pass it your bot's token.
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)

    telegram_bot_token = os.environ.get('bot_token')
    updater = Updater(telegram_bot_token)
    load_lastprice(updater)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("시작", start))
    dp.add_handler(CommandHandler("도움", help))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(CommandHandler("시세", current_price))
    dp.add_handler(CommandHandler('timer', callback_timer, pass_job_queue=True))
    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()

