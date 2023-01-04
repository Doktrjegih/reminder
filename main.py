import json

import telebot
from telebot import types

import credentials

bot = telebot.TeleBot(credentials.TOKEN, parse_mode=None)


# ---------- Просмотр текущих задач ----------
@bot.message_handler(commands=["tasks"])
def task_name(message: types.Message):
    with open("tasks.json", "r", encoding="utf-8") as fd:
        tasks = json.load(fd)
        str_tasks = ""
        for task in tasks:
            str_tasks += str(task) + "\n"
        if str_tasks == '':
            bot.send_message(message.chat.id, 'Задач нет')
        else:
            bot.send_message(message.chat.id, str_tasks)


# ---------- Добавление новой задачи ----------
@bot.message_handler(commands=["new"])
def task_name(message: types.Message):
    bot.send_message(message.chat.id, "Введите задачу:")
    bot.register_next_step_handler(message, task_date)


def task_date(message: types.Message):
    if message.text.lower() == "c":
        cancel(message)
        return
    task = {"name": message.text}
    bot.send_message(message.chat.id, "Введите дату и время (ДД.ММ.ГГГГ_ЧЧ:ММ):")
    bot.register_next_step_handler(message, task_period, task)


# todo: реализация еще не готова
def task_period(message: types.Message, task):
    if message.text.lower() == "c":
        cancel(message)
        return
    task.update({"date": message.text})
    bot.send_message(message.chat.id, "Введите периодичность напоминаний (мин):")
    bot.register_next_step_handler(message, task_save, task)


def task_save(message: types.Message, task):
    if message.text.lower() == "c":
        cancel(message)
        return
    task.update({"period": int(message.text)})
    with open("tasks.json", "r", encoding="utf-8") as fd:
        current_tasks = json.load(fd)
    current_tasks.append(
        {
            "id": len(current_tasks) + 1,
            "name": task["name"],
            "date": task["date"],
            "period": task["period"],
            "status": "active",
        }
    )
    with open("tasks.json", "w", encoding="utf-8") as fd:
        json.dump(current_tasks, fd, indent=4, ensure_ascii=False)
    bot.send_message(
        message.chat.id,
        f'Поставлена задача: {task["name"]} в {task["date"]} с периодичностью {task["period"]} мин',
    )


# ---------- Изменение статуса задачи ----------
@bot.message_handler(commands=["change"])
def change_task(message: types.Message):
    with open("tasks.json", "r", encoding="utf-8") as fd:
        tasks_from_file = json.load(fd)
    str_tasks = ""
    for task in tasks_from_file:
        str_tasks += str(task) + "\n"
    bot.send_message(message.chat.id, f"Введите номер задачи:\n{str_tasks}")
    bot.register_next_step_handler(message, new_task_status)


def new_task_status(message: types.Message):
    if message.text.lower() == "c":
        cancel(message)
        return
    task = {"id": message.text}
    bot.send_message(
        message.chat.id, "Введите нужный статус (d = disable, f = finish, a = active):"
    )
    bot.register_next_step_handler(message, change, task)


def change(message: types.Message, task):
    if message.text.lower() == "c":
        cancel(message)
        return
    if message.text.lower() == "d":
        task.update({"status": "disable"})
    elif message.text.lower() == "f":
        task.update({"status": "finish"})
    elif message.text.lower() == "a":
        task.update({"status": "active"})
    else:
        cancel(message)
        return
    with open("tasks.json", "r", encoding="utf-8") as fd:
        tasks_from_file = json.load(fd)
    with open("tasks.json", "w", encoding="utf-8") as fd:
        tasks_from_file[int(task["id"]) - 1]["status"] = task["status"]
        json.dump(tasks_from_file, fd, indent=4, ensure_ascii=False)
    bot.send_message(
        message.chat.id,
        f"Задача изменена:\n{str(tasks_from_file[int(task['id']) - 1])}",
    )


# ---------- Очистка выполненных задач ----------
@bot.message_handler(commands=["clear"])
def clear(message: types.Message):
    bot.send_message(message.chat.id, "Уверены?")
    bot.register_next_step_handler(message, goodbye_tasks)


def goodbye_tasks(message: types.Message):
    if message.text.lower() == "c":
        cancel(message)
        return
    with open("tasks.json", "r", encoding="utf-8") as fd:
        current_tasks = json.load(fd)
    for task in current_tasks:
        if task["status"] == "finish":
            current_tasks.remove(task)
    for counter, task in enumerate(current_tasks, start=1):
        task["id"] = counter
    with open("tasks.json", "w", encoding="utf-8") as fd:
        json.dump(current_tasks, fd, indent=4, ensure_ascii=False)
    str_tasks = ""
    for task in current_tasks:
        str_tasks += str(task) + "\n"
    bot.send_message(message.chat.id, f"Завершенные задачи удалены:\n{str_tasks}")


# ---------- Отмена действия ----------
def cancel(message: types.Message):
    bot.send_message(message.chat.id, "Отмена действия")


# ---------- Запуск бота ----------
bot.infinity_polling()
