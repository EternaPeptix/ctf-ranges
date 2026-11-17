# ============================================================================
#  The Backlog CTF — control
#    make up       build + start all 15 challenges + scoreboard
#    make check    run every solver in-network (proves all 15 flags)
#    make logs     follow logs
#    make down     stop + remove everything
#    make reset    down + up
# ============================================================================
COMPOSE = docker compose
.PHONY: up check logs down reset

up:
	$(COMPOSE) up -d --build
	@echo
	@echo "Scoreboard:  http://localhost:$${SB_PORT:-8300}"
	@echo "Challenges:  http://localhost:8301 .. 8315"

check:
	./scripts/verify.sh

logs:
	$(COMPOSE) logs -f --tail=80

down:
	$(COMPOSE) down -v

reset: down up
