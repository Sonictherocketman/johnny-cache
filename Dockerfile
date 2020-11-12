FROM python:3.7
MAINTAINER Brian Schrader <brian@brianschrader.com>
EXPOSE 8000
WORKDIR /app


# Virtual Env
RUN pip install virtualenv
RUN (virtualenv cache-proxy)
RUN (. cache-proxy/bin/activate)

RUN (pip install gunicorn && pip install gevent)

# Cache the requirements
COPY requirements.txt .
RUN (pip install -r requirements.txt)

# App setup
COPY . .

# Production Setup
CMD gunicorn johnny_cache.wsgi \
    --worker-connections=2000 \
    --backlog=1000 \
    -p gunicorn.pid \
    -t 60 \
    --bind=0.0.0.0:8000

