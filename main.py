from datetime import timedelta

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram_calendar import simple_cal_callback, SimpleCalendar

import credentials
import db
from db import Reminders

bot = Bot(credentials.TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


# ---------- Просмотр меню ----------
@dp.message_handler(commands=['menu'], state="*")  # тут state важная штука
async def menu(message: types.Message, state: FSMContext) -> None:
    await state.finish()
    active_tasks = KeyboardButton('⏰ Список активных задач')
    all_tasks = KeyboardButton('📋 Список всех задач')
    new_task = KeyboardButton('➕ Новая задача')
    close_task = KeyboardButton('✅ Закрыть задачу')

    greet_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    greet_kb.add(active_tasks)
    greet_kb.add(all_tasks)
    greet_kb.add(new_task)
    greet_kb.add(close_task)
    await message.answer('Показываю меню', reply_markup=greet_kb)


# ---------- Регистратор машины состояний ----------
def register_handlers_common(dp: Dispatcher) -> None:
    # добавление задачи
    dp.register_message_handler(task_name, lambda msg: msg.text == '➕ Новая задача', state="*")
    dp.register_message_handler(task_date, state=NewTask.waiting_for_date)
    # ручная функция календаря, затем вызывающая task_time_hour()
    dp.register_message_handler(task_time_minute, state=NewTask.waiting_for_minutes)
    dp.register_message_handler(repeat, state=NewTask.waiting_for_repeat)
    dp.register_message_handler(notifications, state=NewTask.waiting_for_notifications)
    dp.register_message_handler(deadline, state=NewTask.waiting_for_deadline)
    dp.register_message_handler(check_data, state=NewTask.waiting_for_check)
    dp.register_message_handler(create_new_task, state=NewTask.final)

    # просмотр активных задач
    dp.register_message_handler(get_active_tasks, lambda msg: msg.text == '⏰ Список активных задач', state="*")

    # просмотр активных задач
    dp.register_message_handler(get_all_tasks, lambda msg: msg.text == '📋 Список всех задач', state="*")

    # просмотр активных задач
    dp.register_message_handler(close_task, lambda msg: msg.text == '✅ Закрыть задачу', state="*")
    dp.register_message_handler(accept_answer, state=CloseTask.waiting_for_accept)
    dp.register_message_handler(update_task, state=CloseTask.final)


class NewTask(StatesGroup):
    waiting_for_date = State()
    waiting_for_minutes = State()
    waiting_for_repeat = State()
    waiting_for_notifications = State()
    waiting_for_deadline = State()
    waiting_for_check = State()
    final = State()


class CloseTask(StatesGroup):
    waiting_for_accept = State()
    final = State()


# ---------- Просмотр текущих задач ----------
async def get_active_tasks(message: types.Message, state: FSMContext):
    data: list[Reminders] = db.get_reminders()
    answer = ''
    for task in data:
        answer += f'{task.remind_id, task.name, task.datetime.strftime("%d.%m.%Y %H:%M"), task.repeat_by}\n'
    await message.answer(answer)
    await menu(message, state)


# ---------- Просмотр всех задач ----------
async def get_all_tasks(message: types.Message, state: FSMContext):
    data: list[Reminders] = db.get_all_reminders()
    answer = ''
    for task in data:
        answer += f'{task.remind_id, task.name, task.datetime.strftime("%d.%m.%Y %H:%M"), task.repeat_by}\n'
    await message.answer(answer)
    await menu(message, state)


# ---------- Закрыть задачу: показ текущих задач ----------
async def close_task(message: types.Message):
    data: list[Reminders] = db.get_reminders()
    answer = ''
    tasks_buttons = []
    for task in data:
        tasks_buttons.append(KeyboardButton(task.remind_id))
        answer += f'{task.remind_id, task.name, task.datetime.strftime("%d.%m.%Y %H:%M"), task.repeat_by}\n'
    await message.answer(f'Выберите задачу:\n\n{answer}', reply_markup=get_keyboard(tasks_buttons, 5))
    await CloseTask.next()


# ---------- Закрыть задачу: показ текущих задач ----------
async def accept_answer(message: types.Message, state: FSMContext):
    if message.text == 'В меню':
        await menu(message, state)
        return
    data: Reminders = db.get_certain_reminder(message.text)
    await state.update_data(remind_id=int(message.text))
    await state.update_data(task=data)

    answer = f'Отметить текущую задачу как выполненную?\n\n' \
             f'{data.name}\n' \
             f'{data.datetime.strftime("%d.%m.%Y %H:%M")}\n' \
             f'Тип повторения: {data.repeat_by}\n' \
             f'Напоминания каждые {data.repeat_each * 5} мин\n' \
             f'Дедлайн: {data.deadline}'

    button_1 = KeyboardButton('Да')
    button_2 = KeyboardButton('Нет (в меню)')
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if data.repeat_by == 'daily':
        always_button = KeyboardButton('Закрыть навсегда')
        kb.row(button_1, always_button)
        kb.row(button_2)
    else:
        kb.row(button_1, button_2)
    await message.answer(answer, reply_markup=kb)
    await CloseTask.next()


# ---------- Закрыть задачу: запись в базу ----------
async def update_task(message: types.Message, state: FSMContext):
    if message.text == 'Нет (в меню)':
        await menu(message, state)
        return
    data_ = await state.get_data()
    task = data_["task"]
    db.set_repeat_iter(task.remind_id, 0)
    if message.text == 'Да':
        if task.repeat_by == 'daily':
            db.update_date(task.remind_id, task.datetime + timedelta(days=1))
        elif task.repeat_by == 'never':
            db.mark_as_done(task.remind_id)
    elif message.text == 'Закрыть навсегда':
        db.mark_as_done(task.remind_id)
    data = {"remind_id": task.remind_id, "datetime": task.datetime, "status": 'done'}
    db.add_new_history_entry(data)
    await message.answer('Отметил!')
    await menu(message, state)
    return


# ---------- Добавление задачи: запрос названия ----------
async def task_name(message: types.Message, state: FSMContext):
    await state.finish()

    cancel_button = KeyboardButton('В меню')
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row(cancel_button)

    await message.answer('Введите название:', reply_markup=kb)
    await NewTask.next()


# ---------- Добавление задачи: запрос даты ----------
async def task_date(message: types.Message, state: FSMContext):
    if message.text == 'В меню':
        await menu(message, state)
        return
    await select_date_on_calendar(message, state)


async def select_date_on_calendar(message: types.Message, state: FSMContext) -> None:
    await state.finish()
    await state.update_data(name=message.text)
    await state.update_data(action='new_task')
    await message.answer('Выберите дату:', reply_markup=await SimpleCalendar().start_calendar())


@dp.callback_query_handler(simple_cal_callback.filter())
async def process_simple_calendar(callback_query: CallbackQuery, callback_data: dict, state: FSMContext) -> None:
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if selected:
        start_kb = ReplyKeyboardMarkup(resize_keyboard=True)
        await callback_query.message.answer(
            f'{date.strftime("%d.%m.%Y")}',
            reply_markup=start_kb
        )
        data = await state.get_data()
        if data["action"] == 'new_task':
            await task_time_hour(callback_query.message, state, date)


# ---------- Добавление задачи: запрос времени (час) ----------
async def task_time_hour(message: types.Message, state: FSMContext, date):
    await state.update_data(date=date.strftime('%d.%m.%Y'))
    hours = [str(i) for i in range(0, 24)]
    for i in hours:
        if len(i) == 1:
            hours[hours.index(i)] = '0' + i
    await message.answer('Выберите время (час):', reply_markup=get_keyboard(hours, 6))
    await NewTask.waiting_for_minutes.set()


def get_keyboard(buttons_list, row_len) -> ReplyKeyboardMarkup:
    def func_chunks_generators(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i: i + n]

    cancel_button = KeyboardButton('В меню')
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for chunk in list(func_chunks_generators(buttons_list, row_len)):
        kb.row(*[element for element in chunk])
    kb.row(cancel_button)
    return kb


# ---------- Добавление задачи: запрос времени (минута) ----------
async def task_time_minute(message: types.Message, state: FSMContext):
    if message.text == 'В меню':
        await menu(message, state)
        return
    await state.update_data(hour=message.text)
    minutes = [str(i) for i in range(0, 56, 5)]
    for i in minutes:
        if len(i) == 1:
            minutes[minutes.index(i)] = '0' + i
    await message.answer('Выберите время (минута):', reply_markup=get_keyboard(minutes, 6))
    await NewTask.next()


# ---------- Добавление задачи: выбор типа повторения ----------
async def repeat(message: types.Message, state: FSMContext):
    if message.text == 'В меню':
        await menu(message, state)
        return
    await state.update_data(minute=message.text)

    daily = KeyboardButton('Ежедневно')
    one_time = KeyboardButton('Без повторения')
    cancel_button = KeyboardButton('В меню')
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row(one_time, daily)
    kb.row(cancel_button)

    await message.answer('Тип повторения:', reply_markup=kb)
    await NewTask.next()


# ---------- Добавление задачи: выбор частоты напоминаний ----------
async def notifications(message: types.Message, state: FSMContext):
    if message.text == 'В меню':
        await menu(message, state)
        return
    await state.update_data(repeat_by=message.text)

    notif_by = ['5', '10', '15', '20', '30', '60', '120', '180']
    await message.answer('Частота напоминаний (мин):', reply_markup=get_keyboard(notif_by, 4))
    await NewTask.next()


# ---------- Добавление задачи: выбор дедлайна ----------
async def deadline(message: types.Message, state: FSMContext):
    if message.text == 'В меню':
        await menu(message, state)
        return
    await state.update_data(repeat_each=int(message.text))

    without = KeyboardButton('Без дедлайна')
    cancel_button = KeyboardButton('В меню')
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row(*['30', '60', '120', '180', '360'])
    kb.row(without)
    kb.row(cancel_button)

    await message.answer('Дедлайн (мин):', reply_markup=kb)
    await NewTask.next()


# ---------- Добавление задачи: проверка данных ----------
async def check_data(message: types.Message, state: FSMContext):
    if message.text == 'В меню':
        await menu(message, state)
        return
    if message.text == 'Без дедлайна':
        await state.update_data(deadline='null')
    else:
        await state.update_data(deadline=int(message.text))
    data = await state.get_data()
    answer = f'Всё верно?\n\n' \
             f'{data["name"]}\n' \
             f'{data["date"]}\n' \
             f'{data["hour"]}:{data["minute"]}\n' \
             f'Тип повторения: {data["repeat_by"]}\n' \
             f'Напоминания каждые {data["repeat_each"]} мин\n' \
             f'Дедлайн: {data["deadline"]}'

    button_1 = KeyboardButton('Да')
    button_2 = KeyboardButton('Нет (в меню)')
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row(button_1, button_2)

    await message.answer(answer, reply_markup=kb)
    await NewTask.next()


# ---------- Добавление задачи: проверка данных ----------
async def create_new_task(message: types.Message, state: FSMContext):
    if message.text == 'Нет (в меню)':
        await message.answer('Тогда не добавляю')
        await menu(message, state)
        return
    if message.text == 'Да':
        data = await state.get_data()
        db.add_new_reminder(data)
        await message.answer('Отлично, добавил!')
        await menu(message, state)
        return


# # ---------- Очистка выполненных задач ----------
# @bot.message_handler(commands=["clear"])
# def clear(message: types.Message):
#     bot.send_message(message.chat.id, "Уверены?")
#     bot.register_next_step_handler(message, goodbye_tasks)
#
#
# def goodbye_tasks(message: types.Message):
#     if message.text.lower() == "c":
#         cancel(message)
#         return
#     with open("tasks.json", "r", encoding="utf-8") as fd:
#         current_tasks = json.load(fd)
#     for task in current_tasks:
#         if task["status"] == "finish":
#             current_tasks.remove(task)
#     for counter, task in enumerate(current_tasks, start=1):
#         task["id"] = counter
#     with open("tasks.json", "w", encoding="utf-8") as fd:
#         json.dump(current_tasks, fd, indent=4, ensure_ascii=False)
#     str_tasks = ""
#     for task in current_tasks:
#         str_tasks += str(task) + "\n"
#     bot.send_message(message.chat.id, f"Завершенные задачи удалены:\n{str_tasks}")


# ---------- Запуск машины состояний и бота ----------
register_handlers_common(dp)
executor.start_polling(dp, skip_updates=False)
