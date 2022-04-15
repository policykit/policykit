FROM ubuntu

ENV SERVER_URL=
ENV SLACK_APP_ID=
ENV GITHUB_APP_ID=
ENV SLACK_CLIENT_ID=
ENV GITHUB_APP_NAME=
ENV SENDGRID_API_KEY=
ENV REDDIT_CLIENT_ID=
ENV DISCORD_CLIENT_ID=
ENV DISCORD_BOT_TOKEN=
ENV SLACK_CLIENT_SECRET=
ENV SLACK_SIGNING_SECRET=
ENV REDDIT_CLIENT_SECRET=
ENV DISCORD_CLIENT_SECRET=
ENV GITHUB_PRIVATE_KEY_PATH=

WORKDIR metagov

RUN apt update && apt upgrade -y

RUN apt install python3-pip -y

RUN apt install git -y

RUN echo "DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')" >> .env

COPY policykit metagov

RUN pip3 install --no-cache-dir -r metagov/requirements.txt

RUN bash metagov/celery_script.sh