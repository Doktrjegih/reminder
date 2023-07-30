import asyncio

from datetime import datetime, timedelta

from aiogram import Bot

import credentials
import db


bot = Bot(credentials.TOKEN)


async def start_spam():
    active_tasks = db.get_reminders()
    for task in active_tasks:
        await analysis_time_of_task(task)


# проверка, наступило ли время таски
async def analysis_time_of_task(task):
    now = datetime.now()  # а для Тохи костыль
    if task.datetime < now:
        await analysis_type_of_task(task, now)


# определение типа задачи
async def analysis_type_of_task(task, now):
    if task.repeat_by == 'daily':
        await daily_task(task, now)
    elif task.repeat_by == 'never':
        await one_time_task(task, now)


# работа с ежедневными задачами
async def daily_task(task, now):
    next_day_6_am = task.datetime + timedelta(days=1)
    next_day_6_am = next_day_6_am.replace(hour=6, minute=0, second=0, microsecond=0)
    if not await is_deadline_reached(task, now):
        if now < next_day_6_am:
            await send_repeatable_remind(task)
        else:
            await new_history(task, status='overdue on 6 am')
    else:
        await new_history(task, status='overdue on deadline')


# добавить в базу истории запись о статусе ежедневной задачи
async def new_history(task, status):
    db.set_repeat_iter(task.remind_id, 0)
    db.update_date(task.remind_id, task.datetime + timedelta(days=1))
    data = {"remind_id": task.remind_id, "datetime": task.datetime, "status": status}
    db.add_new_history_entry(data)


# работа с одноразовыми задачами
async def one_time_task(task, now):
    if not await is_deadline_reached(task, now):
        await send_repeatable_remind(task)
    else:
        db.set_overdue(task.remind_id)


# проверка на достижение дедлайна
async def is_deadline_reached(task, now) -> bool:
    if task.deadline:
        if now > task.datetime + timedelta(minutes=task.deadline):
            await bot.send_message(credentials.CHAT_ID, f'пук среньк, таска "{task.name}" протухла по дедлайну')
            return True
        return False


# # отправка напоминания через заданные промежутки времени (старый неточный вариант)
# async def send_repeatable_remind(task):
#     if task.repeat_iter < task.repeat_each:
#         db.increment_repeat_iter(task.remind_id)
#     else:
#         db.set_repeat_iter(task.remind_id, 0)
#         await bot.send_message(credentials.CHAT_ID,
#                                f'{task.name} (напоминание каждые {task.repeat_each * 5} минут)')


# отправка напоминания через заданные промежутки времени (улучшенный и все равно сука косячный вариант)
# async def send_repeatable_remind(task):
#     db.increment_repeat_iter(task.remind_id)
#     updated_task = db.get_certain_reminder(task.remind_id)
#     if updated_task.repeat_iter == updated_task.repeat_each + 1:
#         db.reset_repeat_iter(updated_task.remind_id)
#         await bot.send_message(credentials.CHAT_ID,
#                                f'{updated_task.name} (напоминание каждые {updated_task.repeat_each * 5} минут)')


# отправка напоминания через заданные промежутки времени (возможно будет работать)
async def send_repeatable_remind(task):
    task.repeat_iter += 1
    if task.repeat_iter > task.repeat_each:
        db.set_repeat_iter(task.remind_id, 1)
        await bot.send_message(credentials.CHAT_ID,
                               f'{task.name} (напоминание каждые {task.repeat_each * 5} минут)')


def main():
    asyncio.run(start_spam())


main()
