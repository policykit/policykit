# _**PolicyKit**_

PolicyKit empowers online community members to concisely author a wide range of governance procedures and automatically
carry out those procedures on their home platforms. Inspired by Nobel economist Elinor Ostrom, we’ve developed a
framework that describes governance as a series of actions and policies, written in short programming scripts. We’re now
building out an editor, software libraries, and connectors to platforms like Slack, Reddit, and Discord for communities
to author actions and policies.

## How to install Policykit:

####check out our docs for installing without Docker:
```
https://policykit.readthedocs.io/en/latest/index.html
```

#### Installing with Docker:

```
docker-compose up --build -d --force-recreate
```

###This docker-compose consists of the following images:
1. Policykit: This builds the official policykit image
2. RabbitMq: This is used as a broker for celery tasks
3. Cadvisor: This is used to monitor container metrics
4. Database: We use postgres as a database for policykit
5. Prometheus: This is a time-series db for storing server metrics
6. Grafana: This is used to monitor the server this app is deployed on
7. Node Exporter: This is used as an agent to export server metrics to prometheus


## Important Notes before installing:
1. The only required containers for this deployemnt is Policykit, Database, and Rabbitmq, rest all can be removed if
not needed, they are just for monitoring
2. It's recommended to use with docker to avoid making changes to the code but if one needs to deploy this without
doker, here are the changes to make:
   1. Create an external postgres database or just comment the postgres lines from settings.py and uncomment
   sqlite to get going
   2. Make sure to remove the broker keyword from policykit celery.py if docker is not used
