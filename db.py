import datetime

from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.query import Query

engine = create_engine('sqlite:///database.sqlite', echo=False)
base = declarative_base()


class Reminders(base):
    __tablename__ = 'reminders'

    remind_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    datetime = Column(DateTime)
    repeat_each = Column(Integer)
    repeat_iter = Column(Integer)
    status = Column(String)
    repeat_by = Column(String)
    deadline = Column(Integer)

    def __init__(self, name, datetime, repeat_each, repeat_iter, status, repeat_by, deadline):
        self.name = name
        self.datetime = datetime
        self.repeat_each = repeat_each
        self.repeat_iter = repeat_iter
        self.status = status
        self.repeat_by = repeat_by
        self.deadline = deadline


class History(base):
    __tablename__ = 'history'

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    remind_id = Column(Integer)
    datetime = Column(DateTime)
    status = Column(String)
    timelog = Column(DateTime)

    def __init__(self, remind_id, datetime, status, timelog):
        self.remind_id = remind_id
        self.datetime = datetime
        self.status = status
        self.timelog = timelog


# штука нужная для создания БД в первый раз
# base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


def get_reminders() -> list[Query]:
    return session.query(
        Reminders,
    ).filter(Reminders.status == 'active').all()


def get_all_reminders() -> list[Query]:
    return session.query(
        Reminders,
    ).all()


def get_certain_reminder(remind_id: int) -> Query:
    return session.query(
        Reminders,
    ).filter(Reminders.remind_id == remind_id).first()


def increment_repeat_iter(remind_id: int) -> None:
    session.query(Reminders).filter(Reminders.remind_id == remind_id).first().repeat_iter += 1
    session.commit()


def set_repeat_iter(remind_id: int, value: int) -> None:
    session.query(Reminders).filter(Reminders.remind_id == remind_id).first().repeat_iter = value
    session.commit()


def update_date(remind_id: int, new_time: datetime) -> None:
    session.query(Reminders).filter(Reminders.remind_id == remind_id).first().datetime = new_time
    session.commit()


def set_overdue(remind_id: int) -> None:
    session.query(Reminders).filter(Reminders.remind_id == remind_id).first().status = 'overdue'
    session.commit()


def mark_as_done(remind_id: int) -> None:
    session.query(Reminders).filter(Reminders.remind_id == remind_id).first().status = 'done'
    session.commit()


def add_new_history_entry(data):
    remind_id = data["remind_id"]
    datetime_ = data["datetime"]
    status = data["status"]
    timelog = datetime.datetime.now()

    tr = History(remind_id, datetime_, status, timelog)
    session.add(tr)
    session.commit()


def add_new_reminder(data: Reminders):
    name = data["name"]
    datetime_ = datetime.datetime.strptime(f'{data["date"]} {data["hour"]}:{data["minute"]}', '%d.%m.%Y %H:%M')
    repeat_each = data["repeat_each"] / 5
    repeat_iter = 0
    status = 'active'
    repeat_by = 'daily' if data["repeat_by"] == 'Ежедневно' else 'never'
    deadline = data["deadline"] if data["deadline"] != 'null' else None
    tr = Reminders(name=name,
                   datetime=datetime_,
                   repeat_each=repeat_each,
                   repeat_iter=repeat_iter,
                   status=status,
                   repeat_by=repeat_by,
                   deadline=deadline)
    session.add(tr)
    session.commit()
