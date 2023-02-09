import os

import datetime
import shutil

from aiogram.types import InputFile
import credentials
from aiogram import Bot
import asyncio

bot = Bot(token=credentials.TOKEN)


async def send_backup():
    name = f'reminder_backup_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.sqlite'
    shutil.copy('database.sqlite', name)
    file = InputFile(name)
    await bot.send_document(credentials.CHAT_ID, file)
    os.remove(name)


def main():
    asyncio.run(send_backup())


main()
