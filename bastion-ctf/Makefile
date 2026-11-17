# ============================================================================
#  Bastion CTF range — control
#    make up      build + start the app
#    make check   run the automated solver (proves every flag)
#    make logs    follow logs
#    make down    stop + remove
#    make reset   down + up
# ============================================================================
COMPOSE = docker compose
.PHONY: up check logs down reset

up:
	$(COMPOSE) up -d --build
	@echo
	@echo "Bastion:  http://localhost:$${WEB_PORT:-8080}"

check:
	./scripts/verify.sh

logs:
	$(COMPOSE) logs -f --tail=60

down:
	$(COMPOSE) down -v

reset: down up
