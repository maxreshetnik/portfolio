ifeq ($(RACK_ENV), dev)
name_prefix = example-
endif
RACK_ENV ?= prod
SECRETS_DIR ?= ./conf
backend_id = "$$(docker $(opts) ps | grep 'backend' | awk '{ print $$1 }')"
-include $(SECRETS_DIR)/$(name_prefix)web.env $(SECRETS_DIR)/$(name_prefix)db.env
export DOMAIN_NAME SSL_EMAIL

demo: db-check
	./manage.py testserver --noinput example_shop_data.json

.PHONY: admin collect db demo loaddata migrate runserver setup start test \
build up prune down logs ps swarm deploy secrets

runserver: dev-check
	./manage.py runserver --nothreading

start: collect
ifeq (,$(GUNICORN_CMD_ARGS))
	gunicorn --bind=127.0.0.1:8000 --reload --access-logfile - portfolio.wsgi
endif
	# GUNICORN_CMD_ARGS=$(GUNICORN_CMD_ARGS)
	gunicorn portfolio.wsgi

db:
	DB_ENV_FILE=$(SECRETS_DIR)/$(name_prefix)db.env \
	./conf/db-init-user.sh

db-drop: dev-check
	psql --username "$(POSTGRES_USER)" --dbname "$(POSTGRES_DB)" \
	-c "DROP DATABASE $(PORTFOLIO_DB_USER);"
	psql --username "$(POSTGRES_USER)" --dbname "$(POSTGRES_DB)" \
	-c "DROP USER $(PORTFOLIO_DB_USER);"

setup: db-check migrate admin loaddata

admin:
	DJANGO_SUPERUSER_PASSWORD=admin \
	./manage.py createsuperuser --username admin \
	--email "admin@admin.com" --noinput

collect:
	./manage.py collectstatic --no-input

db-check:
	./manage.py check --database default

dev-check:
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

down-v: dev-check
	docker-compose down -v

logs:
	docker-compose logs --tail=10

ps:
	docker-compose ps --all

prune: dev-check
	docker-compose down -v --rmi all
	docker $(opts) image prune -f

backend-setup: dev-check backend-check-db backend-migrate-check
ifneq (,$(media))
	make backend-loadmedia src=$(media)
endif
	make backend-loaddata src=$(data)
	@make backend-admin vars="DJANGO_SUPERUSER_PASSWORD=admin" \
	args="--email admin@admin.com --noinput"

backend-admin:
	@docker $(opts) exec -it $(backend_id) \
	bash -c ' $(vars) ./manage.py createsuperuser --username admin $(args)'

backend-migrate: backend-check-db
	docker $(opts) exec -it $(backend_id) \
	./manage.py makemigrations && ./manage.py migrate

backend-migrate-check:
	docker $(opts) exec -it $(backend_id) \
	./manage.py migrate --check

backend-check: backend-check-db backend-check-deploy
			
backend-check-db:
	docker $(opts) exec -it $(backend_id) \
	./manage.py check --database default
			
backend-check-deploy:
	docker $(opts) exec -it $(backend_id) \
	./manage.py check --deploy

backend-loaddata:
	docker $(opts) cp "$(src)" $(backend_id):/home/portfolio/data.json
	docker $(opts) exec -it $(backend_id) \
	./manage.py loaddata /home/portfolio/data.json ; \
	docker $(opts) exec -it $(backend_id) \
	rm /home/portfolio/data.json

backend-loadmedia:
	docker $(opts) cp "$(src)" $(backend_id):/home/portfolio/
	
backend-test:
	docker $(opts) exec -it $(backend_id) \
	./manage.py test --verbosity 2

# Docker Swarm targets, for prod.
# docker-compose.yml and docker-compose.stack.yml files.
stack-push: stack-build
	docker-compose --log-level ERROR \
	-f ./docker-compose.yml -f ./docker-compose.stack.yml \
	push backend

stack-build:
	docker-compose --log-level ERROR \
	-f ./docker-compose.yml -f ./docker-compose.stack.yml \
	build --compress backend

stack-pull:
	docker-compose --log-level ERROR \
	-f ./docker-compose.yml -f ./docker-compose.stack.yml \
	pull

swarm:
	docker $(opts) swarm init --advertise-addr eth0

deploy: stack-pull secrets
	docker $(opts) stack deploy \
	-c ./docker-compose.yml -c ./docker-compose.stack.yml portfolio

secrets: stack-rm secrets-prune
	make secret-create name=secrets.json
	make secret-create name=db.env
	# Secret creation completed.

secrets-prune: stack-rm
	make secret-rm name=secrets.json
	make secret-rm name=db.env
	# Cleaning up secrets is complete.

secret-rm:
	docker $(opts) secret rm portfolio_$(name) || echo "error $$?"
	
secret-create:
	docker $(opts) secret create --label env=$(RACK_ENV) \
	--label rev="$$(date +"%Y%m%d")" \
	portfolio_$(name) $(SECRETS_DIR)/$(name_prefix)$(name)

stack-prune: dev-check stack-rm secrets-prune
	docker $(opts) image prune --all -f
	docker $(opts) volume prune -f

stack-rm:
	docker $(opts) stack rm portfolio

stack-info:
	docker $(opts) stack ps portfolio
	docker $(opts) stack services portfolio

service-logs:
	docker $(opts) stack ps --filter "name=portfolio_$(s)" portfolio
	docker $(opts) service logs --since 1m --no-task-ids -t --raw portfolio_$(s)

