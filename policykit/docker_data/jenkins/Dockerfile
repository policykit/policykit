FROM jenkins/jenkins:lts

USER root

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update && apt upgrade -y

RUN apt install apt-utils -y

RUN apt install python3-pip -y

RUN pip3 install python-dateutil

RUN apt install virtualenv -y

RUN apt install jq -y

RUN apt install sudo

RUN rm -rf /var/lib/apt/lists/*

RUN echo "jenkins ALL=NOPASSWD: ALL" >> /etc/sudoers

RUN apt update

RUN apt install apt-transport-https ca-certificates curl software-properties-common -y

RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

RUN add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"

RUN apt update

RUN apt install docker-ce -y

RUN curl -L "https://github.com/docker/compose/releases/download/1.28.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

RUN chmod +x /usr/local/bin/docker-compose