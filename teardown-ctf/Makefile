# ============================================================================
#  Teardown CTF — control
#    make up      build + start all five challenges + the scoreboard
#    make check   run the full pwntools solver in-network (all 5 flags), exit 0
#    make logs / down / reset
# ============================================================================
COMPOSE = docker compose
.PHONY: up check logs down reset

up:
	./scripts/build.sh
	@echo
	@echo "Scoreboard:  http://localhost:$${SB_PORT:-8506}"
	@echo "Challenges:  nc localhost 9001 .. 9005"

check:
	./scripts/verify.sh

logs:
	$(COMPOSE) logs -f --tail=100

down:
	$(COMPOSE) down -v

reset: down up
