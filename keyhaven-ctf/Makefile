# ============================================================================
#  Keyhaven CTF range ("Null Cipher") — control
#    make up        build + start the whole range
#    make up-edge   bring up just edge + sso (fast loop while building)
#    make check     run the automated end-to-end solver
#    make logs      follow logs
#    make ps        container status
#    make down      stop + remove everything incl. volumes
#    make reset     down + up
# ============================================================================
COMPOSE = docker compose
.PHONY: up up-edge check logs ps down reset

up:
	$(COMPOSE) up -d --build
	@echo
	@echo "Edge (start here):  http://localhost:$${EDGE_PORT:-8080}"
	@echo "Everything else is corp-internal (no host ports). Smuggle in."

up-edge:
	$(COMPOSE) up -d --build edge sso
	@echo "Edge: http://localhost:$${EDGE_PORT:-8080}  (edge + sso only)"

check:
	./scripts/verify.sh

logs:
	$(COMPOSE) logs -f --tail=60

ps:
	$(COMPOSE) ps

down:
	$(COMPOSE) down -v

reset: down up
