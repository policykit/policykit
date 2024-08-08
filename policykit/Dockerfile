FROM python:3.6

WORKDIR app

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
RUN adduser \
        --disabled-password \
        --no-create-home \
        django-user

COPY policykit app

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

USER django-user
