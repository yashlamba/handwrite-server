FROM python:3.8-slim-buster

WORKDIR /app

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6 -y
RUN apt-get install -y fontforge potrace git
RUN git clone --depth 1 --branch main https://github.com/cod-ed/handwrite
RUN cd handwrite && pip install -e .
ENV PORT=5000
COPY . .
RUN pip install -r requirements.txt
COPY default.json default.json

CMD ["gunicorn", "app:create_app()", "--log-level", "debug", "--timeout", "90", "--workers", "2", "--max-requests", "20", "--config", "config.py"]