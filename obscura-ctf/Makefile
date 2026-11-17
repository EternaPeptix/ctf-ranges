# ============================================================================
#  Obscura CTF range — control
#    make up       build + start all 5 widgets + scoreboard
#    make check    run every solver in-network (proves all 5 flags) — exit 0
#    make logs     follow logs
#    make down     stop + remove everything
#    make reset    down + up
# ============================================================================
COMPOSE = docker compose
.PHONY: up check logs down reset

up:
	$(COMPOSE) up -d --build
	@echo
	@echo "Scoreboard:  http://localhost:$${SB_PORT:-8600}"
	@echo "Widgets:     http://localhost:8601 .. 8605"

check:
	./scripts/verify.sh

logs:
	$(COMPOSE) logs -f --tail=80

down:
	$(COMPOSE) down -v

reset: down up
