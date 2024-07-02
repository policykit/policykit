FROM python:3.6

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt && \ 
    adduser \                                           
        --disabled-password \
        --no-create-home \
        django-user

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

USER django-user
