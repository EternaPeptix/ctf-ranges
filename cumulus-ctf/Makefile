# ============================================================================
#  Cumulus CTF — control
#    make up      build + start the platform + scoreboard
#    make check   run the full kill-chain solver in-network (4 flags), exit 0
#    make logs / down / reset
# ============================================================================
COMPOSE = docker compose
.PHONY: up check logs down reset

up:
	$(COMPOSE) up -d --build
	@echo
	@echo "Public app:  http://localhost:$${WEB_PORT:-8097}"
	@echo "Scoreboard:  http://localhost:$${SB_PORT:-8507}"

check:
	./scripts/verify.sh

logs:
	$(COMPOSE) logs -f --tail=100

down:
	$(COMPOSE) down -v

reset: down up
