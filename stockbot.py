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


from telegram.ext import Updater, CommandHandler
import logging
import requests
import json
import os
from os.path import join, dirname
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

coins = ['btc', 'eth', 'xrp', 'etc']
martkets = ['bitfinex', 'coinone', 'korbit']

last_price = {
}

current_price = {
}

chatroom_coin_info = {
}

market_coin_dict = {
    'korbit': {'btc': 'btc_krw', 'eth': 'eth_krw', 'xrp': 'xrp_krw', 'etc': 'etc_krw'},
    'coinone': {'btc': 'btc', 'eth': 'eth', 'xrp': 'xrp', 'etc': 'etc'},
    'bitfinex': {'btc': 'btcusd', 'eth': 'ethusd', 'xrp': 'xrpusd', 'etc': 'etcusd'}
}


def save_lastprice():
    with open('data.json', 'w') as data_file:
        json.dump(last_price, data_file)
    with open('chatroom_coin_info.json', 'w') as data_file:
        json.dump(chatroom_coin_info, data_file)


def load_lastprice(updater):
    global last_price
    global chatroom_coin_info

    try:
        with open('data.json') as data_file:
            last_price = json.load(data_file)
    except:
        pass
    try:
        with open('chatroom_coin_info.json') as data_file:
            chatroom_coin_info = json.load(data_file)
    except:
        pass

    updater.job_queue.run_repeating(callback_alarm, 30, first=True)


coinname_dict = {'btc': 'BTC 비트코인', 'eth': 'ETH 이더리움', 'xrp': 'XRP 리플', 'etc': 'ETC 이더리움클래식'}


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    update.message.reply_text('Hi!')


def help(bot, update):
    update.message.reply_text('/시세 : 현재 종합 시세 보기\n/알람 btc 5% : 비트코인이 5% 변할 때 마다 알려주기\n\n지원 코인 '+coins.join(','))


def echo(bot, update):
    update.message.reply_text(update.message.text)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def update_korbit_current():
    global current_price
    current_market_price = {}
    for (coin, marketcoinname) in market_coin_dict['korbit'].items():
        ret = requests.get('https://api.korbit.co.kr/v1/ticker?currency_pair=' + marketcoinname)
        r = json.loads(ret.text)
        value = int(r['last'])
        current_market_price[coin] = value
    current_price['korbit'] = current_market_price


def update_coinone_current():
    global current_price
    current_market_price = dict()
    for (coin, marketcoinname) in market_coin_dict['coinone'].items():
        ret = requests.get('https://api.coinone.co.kr/ticker/?currency='+marketcoinname)
        r = json.loads(ret.text)
        value = int(r['last'])
        current_market_price[coin] = value
    current_price['coinone'] = current_market_price


def update_bitfinex_current():
    global current_price
    current_market_price = {}
    for (coin, marketcoinname) in market_coin_dict['bitfinex'].items():
        ret = requests.get('https://api.bitfinex.com/v1/pubticker/'+marketcoinname)
        if ret.status_code == 200:
            r = json.loads(ret.text)
            value = float(r['last_price'])
            current_market_price[coin] = value
        else:
            return
    current_price['bitfinex'] = current_market_price


def make_msg(room, only_coin=None, updown=""):
    msg = ''
    global last_price
    for coin in coins:
        if only_coin and only_coin != coin: continue
        msg = msg + "\n\n{}{}".format(coinname_dict[coin], updown)
        for market in martkets:
            current = current_price[market][coin]
            try:
                lastprice = last_price[room][market][coin]
                diffprice = current - lastprice
            except:
                diffprice = 0
            if market == 'bitfinex':
                msg = msg + "\n`{:10} ${:>11,.4f}({:+.4f})`".format(market, current, diffprice)
            else:
                msg = msg + "\n`{:10} {:>11,d}원({:+d})`".format(market, current, diffprice)
            try:
                last_price[room][market][coin] = current
            except KeyError:
                try:
                    last_price[room][market] = {coin: current}
                except KeyError:
                    last_price[room] = {market: {coin: current}}

    save_lastprice()
    return msg


def update_market_price():
    update_coinone_current()
    update_korbit_current()
    update_bitfinex_current()


def check_current_price(bot, update):
    update_market_price()
    update.message.reply_text(make_msg(update.message.chat_id), parse_mode='Markdown')


def callback_alarm(bot, job):
    # check last and current
    update_market_price()
    for (room, coininfo) in chatroom_coin_info.items():
        for (coin, sensitivity) in coininfo.items():
            check = False
            updown = ""
            for (market, market_coinprice) in current_price.items():
                value = market_coinprice[coin]
                try:
                    last_value = last_price[room][market][coin]

                    if value > last_value * (1.0 + sensitivity):
                        check = True
                        updown = "❤️"
                    if value < last_value * (1.0 - sensitivity):
                        check = True
                        updown = "💙"

                    if value > last_value * (1.0 + sensitivity) or value < last_value * (1.0 - sensitivity):
                        check = True
                except:
                    check = True
            if check:
                bot.send_message(chat_id=room,
                                text=make_msg(room, only_coin=coin, updown=updown), parse_mode='Markdown')


def callback_timer(bot, update, job_queue):
    msg_list = update.message.text.split(' ')
    if len(msg_list) != 3:
        bot.send_message(chat_id=update.message.chat_id,
                         text='알람설정 `/알람 [코인종류] [민감도]%`', parse_mode='Markdown')
        return
    coin = msg_list[1].lower()
    global chatroom_coin_info
    bot.send_message(chat_id=update.message.chat_id,
                     text='시세알람 타이머 동작')
    if update.message.chat_id in chatroom_coin_info:
        chatroom_coin_info[update.message.chat_id][coin]=float(msg_list[2].strip('%'))/100
    else:
        chatroom_coin_info[update.message.chat_id]={coin:float(msg_list[2].strip('%'))/100}
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
    dp.add_handler(CommandHandler("안녕", start))
    dp.add_handler(CommandHandler("도움", help))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(CommandHandler("시세", check_current_price))
    dp.add_handler(CommandHandler('알람', callback_timer, pass_job_queue=True))
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

