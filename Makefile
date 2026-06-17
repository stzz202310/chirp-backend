IMAGE = chirp/back-end:latest
COMPOSE = docker compose -f docker-compose.prod.yml

.PHONY: build up down stop logs shell migrate test

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

stop:
	$(COMPOSE) stop

logs:
	$(COMPOSE) logs --tail=100 -f

shell:
	docker exec -it chirp_web /bin/bash

migrate:
	docker exec chirp_web python manage.py migrate

test:
	docker exec chirp_web python manage.py test
