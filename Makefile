ifeq ($(RACK_ENV), dev)
name_prefix = example-
DOMAIN_NAME ?= localhost
SSL_EMAIL ?= admin@localhost
endif

PROJECT_NAME ?= portfolio
RACK_ENV ?= prod
SECRETS_DIR ?= ./conf
backend_id = "$$(docker ps | grep 'backend' | awk '{ print $$1 }')"
export DOMAIN_NAME SSL_EMAIL

demo: db_check
	./manage.py testserver --noinput example_shop_data.json

.PHONY: admin collect db demo loaddata migrate runserver setup start test \
build up prune down logs ps swarm deploy secrets

runserver: dev_check
	./manage.py runserver --nothreading

start: collect
ifeq (,$(GUNICORN_CMD_ARGS))
	gunicorn --bind=127.0.0.1:8000 --reload --access-logfile - $(PROJECT_NAME).wsgi
endif
	# GUNICORN_CMD_ARGS=$(GUNICORN_CMD_ARGS)
	gunicorn $(PROJECT_NAME).wsgi

db:
	DB_ENV_FILE=$(SECRETS_DIR)/$(name_prefix)db.env \
	./conf/db-init-user.sh

db_drop: dev_check
	psql --username "$(POSTGRES_USER)" --dbname "$(POSTGRES_DB)" \
	-c "DROP DATABASE $(PORTFOLIO_DB_USER);"
	psql --username "$(POSTGRES_USER)" --dbname "$(POSTGRES_DB)" \
	-c "DROP USER $(PORTFOLIO_DB_USER);"

setup: db_check migrate admin loaddata

admin:
	DJANGO_SUPERUSER_PASSWORD=admin \
	./manage.py createsuperuser --username admin \
	--email "admin@admin.com" --noinput

collect:
	./manage.py collectstatic --no-input

db_check:
	./manage.py check --database default

dev_check:
ifneq ($(RACK_ENV), dev)
	# Allowed only in a development environment, 
	# set RACK_ENV variable to dev.
	false
endif

test:
	./manage.py test --verbosity 2

migrate: makemigrations
	./manage.py migrate

makemigrations:
	./manage.py makemigrations

loaddata:
ifeq ($(RACK_ENV), dev)
	./manage.py loaddata example_shop_data.json
else
	# ./manage.py loaddata $(data)
	@./manage.py loaddata $(data) \
	|| echo "Provide variable data=/path/to/fixtures/data.json"
endif

# Docker and compose targets, for example and testing.
# docker-compose.yml and docker-compose.override.yml files
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

down_v: dev_check
	docker-compose down -v

logs:
	docker-compose logs --tail=15

ps:
	docker-compose ps --all

prune: dev_check
	docker-compose down -v --rmi all
	docker image prune -f

backend_setup: dev_check backend_check_db backend_migrate_check
ifneq (,$(media))
	make backend_loadmedia src=$(media)
endif
	make backend_loaddata src=$(data)
	@make backend_admin vars="DJANGO_SUPERUSER_PASSWORD=admin" \
	args="--email admin@admin.com --noinput"

backend_admin:
	@docker exec -it $(backend_id) \
	bash -c ' $(vars) ./manage.py createsuperuser --username admin $(args)'

backend_migrate: backend_check_db
	docker exec -it $(backend_id) \
	./manage.py makemigrations && ./manage.py migrate

backend_migrate_check:
	docker exec -it $(backend_id) \
	./manage.py migrate --check

backend_check: backend_check_db backend_check_deploy
			
backend_check_db:
	docker exec $(backend_id) \
	./manage.py check --database default
			
backend_check_deploy:
	docker exec $(backend_id) \
	./manage.py check --deploy

backend_loaddata:
	docker cp $(src) $(backend_id):/home/$(PROJECT_NAME)/data.json
	docker exec -it $(backend_id) \
	./manage.py loaddata /home/$(PROJECT_NAME)/data.json ; \
	docker exec -it $(backend_id) \
	rm /home/$(PROJECT_NAME)/data.json

backend_loadmedia:
	docker cp "$(src)" $(backend_id):/home/$(PROJECT_NAME)/
	
backend_test:
	docker exec $(backend_id) \
	./manage.py test --verbosity 2

# Docker Swarm targets, for prod.
# docker-compose.yml and docker-compose.stack.yml files.
stack_push: stack_build
	docker-compose --log-level ERROR \
	-f ./docker-compose.yml -f ./docker-compose.stack.yml \
	push backend

stack_build:
	docker-compose --log-level ERROR \
	-f ./docker-compose.yml -f ./docker-compose.stack.yml \
	build --compress

stack_pull:
	docker-compose --log-level ERROR \
	-f ./docker-compose.yml -f ./docker-compose.stack.yml \
	pull

swarm:
	docker swarm init --advertise-addr eth0

deploy: stack_pull
	docker stack deploy --prune \
	-c ./docker-compose.yml -c ./docker-compose.stack.yml $(PROJECT_NAME)

secrets:
	make secret_create name=secrets.json
	make secret_create name=db.env
	# Secret creation completed.

secrets_prune: stack_rm
	make secret_rm name=secrets.json
	make secret_rm name=db.env
	# Cleaning up secrets is complete.

secret_rm:
	docker secret rm $(PROJECT_NAME)_$(name) || echo "error $$?"
	
secret_create:
	docker secret create --label env=$(RACK_ENV) \
	--label rev="$$(date +'%Y%m%d')" \
	$(PROJECT_NAME)_$(name) $(SECRETS_DIR)/$(name_prefix)$(name)

stack_prune: dev_check stack_rm secrets_prune
	docker image prune --all -f
	docker volume prune -f

stack_rm:
	docker stack rm $(PROJECT_NAME)

stack_info:
	docker stack ps --no-trunc $(PROJECT_NAME)
	docker stack services $(PROJECT_NAME)
	docker ps

service_logs:
	docker service ps --no-trunc $(PROJECT_NAME)_$(s)
	docker service logs --no-trunc --no-task-ids \
	-n 10 -t --details $(PROJECT_NAME)_$(s)
	docker logs -n 20 "$$(docker ps | grep '$(s)' | awk '{ print $$1 }')"

service_exec:
	docker exec -it \
	"$$(docker ps | grep '$(s)' | awk '{ print $$1 }')" $(c)

service_update:
	docker service update --force $(opts) $(PROJECT_NAME)_$(s)

