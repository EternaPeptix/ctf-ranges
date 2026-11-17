# ============================================================================
#  The Audit CTF — control
#    make up      build + start every service + the scoreboard
#    make check   run the full solver in-network (proves all 5 flags), exit 0
#    make logs    follow logs
#    make down    stop + remove everything
#    make reset   down + up
# ============================================================================
COMPOSE = docker compose
.PHONY: up check logs down reset

up:
	$(COMPOSE) up -d --build
	@echo
	@echo "Scoreboard:   http://localhost:$${SB_PORT:-8505}"
	@echo "Web app:      http://localhost:$${APP_PORT:-8096}"
	@echo "Postgres:     localhost:$${PG_PORT:-55432}   MySQL: localhost:$${MY_PORT:-33306}   SSH: localhost:$${SSH_PORT:-2222}"

check:
	./scripts/verify.sh

logs:
	$(COMPOSE) logs -f --tail=100

down:
	$(COMPOSE) down -v

reset: down up
