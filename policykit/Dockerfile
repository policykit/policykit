# Python 3.10 is the latest version supported by Django 3.2
FROM python:3.10

# RUN apt-get update \
#   && apt-get install -yq --no-install-recommends libfuse-dev nano fuse vim git graphviz \
#   && apt-get clean \
#   && rm -rf /var/lib/apt/lists/*

WORKDIR /app/policykit

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
RUN adduser \
        --disabled-password \
        --no-create-home \
        django-user

COPY policykit policykit

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

USER django-user

# https://stackoverflow.com/a/67832444
ENV PYTHONUNBUFFERED=1
