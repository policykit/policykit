FROM ubuntu

WORKDIR metagov

RUN apt update && apt upgrade -y

RUN apt install python3-pip -y

RUN apt install git -y

COPY policykit metagov

RUN pip3 install --no-cache-dir -r metagov/requirements.txt

RUN python3 metagov/generate_env.py

RUN bash metagov/celery_script.sh