FROM python:3.8-slim-buster

WORKDIR /app

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6 -y
RUN apt-get install -y fontforge potrace git
RUN apt-get install -y libjpeg-dev libtiff5-dev libpng-dev libfreetype6-dev libgif-dev libgtk-3-dev libxml2-dev libpango1.0-dev libcairo2-dev libspiro-dev libuninameslist-dev python3-dev ninja-build cmake build-essential gettext
RUN git clone --depth 1 https://github.com/fontforge/fontforge
RUN cd fontforge && mkdir build && cd build && cmake -GNinja .. && ninja && ninja install
# RUN cp /usr/local/lib/python/dist-packages/* /usr/lib/python/dist-packages
RUN git clone --depth 1 --branch server https://github.com/cod-ed/handwrite
RUN cd handwrite && pip install -e .
ENV PORT=5000
# RUN cd ..
COPY . .
RUN pip install -r requirements.txt
COPY default.json default.json

CMD ["gunicorn", "app:create_app()", "--log-level", "debug", "--timeout", "90", "--workers", "2", "--max-requests", "10", "--config", "config.py"]