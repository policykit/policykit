docker compose run --rm frontend yarn build 
docker compose exec web python manage.py collectstatic --noinput
docker compose restart web