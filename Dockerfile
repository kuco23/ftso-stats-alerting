FROM python:3.13

RUN apt-get clean && apt-get update && \
    apt-get install -y --no-install-recommends \
           gosu

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt --src=/pip-repos

COPY . /app