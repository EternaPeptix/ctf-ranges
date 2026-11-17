# ============================================================================
#  The Gauntlet CTF — control
#    make up      build + start the chain, deploy all 7 challenges, start the board
#    make check   run every exploit in-network (proves all 7 flags), exit 0
#    make logs    follow logs
#    make down    stop + remove everything (incl. volumes)
#    make reset   down + up
# ============================================================================
COMPOSE = docker compose
.PHONY: up check logs down reset

up:
	$(COMPOSE) up -d --build
	@echo
	@echo "Chain RPC:   http://localhost:$${RPC_PORT:-8549}"
	@echo "Scoreboard:  http://localhost:$${SB_PORT:-8504}"

check:
	./scripts/verify.sh

logs:
	$(COMPOSE) logs -f --tail=100

down:
	$(COMPOSE) down -v

reset: down up
