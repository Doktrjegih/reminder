import json
import time

import telebot
import credentials
from datetime import datetime

bot = telebot.TeleBot(credentials.TOKEN, parse_mode=None)


def send_by_time_json():
    while True:
        time.sleep(60)
        with open("tasks.json", "r", encoding="utf-8") as fd:
            tasks_from_file = json.load(fd)
            for task in tasks_from_file:
                date = datetime.strptime(task["date"], "%d.%m.%Y_%H:%M")
                status = task["status"]
                if status == "active" and date < datetime.now():
                    send_spam(task)
        fd.close()


def send_spam(task):
    bot.send_message(credentials.CHAT_ID, f"Делай таску: {task}, ублюдина")


send_by_time_json()
