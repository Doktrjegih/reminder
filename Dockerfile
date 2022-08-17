FROM python:3.10-alpine

WORKDIR app/

ENV TZ=Asia/Yekaterinburg

COPY requirements.txt .

RUN pip install -U pip
RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT ["python3", "main.py"]