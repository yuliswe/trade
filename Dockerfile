FROM python:3

# RUN apt-get update && \
#     apt-get install -y python3 python3-pip
RUN pip3 install --upgrade pip
RUN pip3 install poetry
RUN mkdir /trade
WORKDIR /trade
COPY pyproject.toml poetry.lock ./
RUN poetry install
COPY . /trade
ENTRYPOINT poetry run trade.py
