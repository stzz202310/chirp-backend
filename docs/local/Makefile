IMAGE = chirp/back-end:latest

.PHONY: build up down stop logs shell migrate test

build:
	docker build -t $(IMAGE) .

up:
	docker compose up -d

down:
	docker compose down

stop:
	docker compose stop

logs:
	docker compose logs --tail=100 -f

shell:
	docker compose exec chirp /bin/bash

migrate:
	docker compose exec chirp python manage.py migrate

test:
	docker compose exec chirp python manage.py test