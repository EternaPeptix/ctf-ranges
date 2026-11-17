# ============================================================================
#  Puppeteer CTF — control
#    make up      build + start the agentic platform + scoreboard
#    make check   run the full kill-chain solver in-network (proves all 6 flags)
#    make logs    follow logs
#    make down    stop + remove everything (incl. volumes)
#    make reset   down + up
# ============================================================================
COMPOSE = docker compose
.PHONY: up check logs down reset

up:
	$(COMPOSE) up -d --build
	@echo
	@echo "Chat / agent:  http://localhost:$${CHAT_PORT:-8500}"
	@echo "Scoreboard:    http://localhost:$${SB_PORT:-8501}"

check:
	./scripts/verify.sh

logs:
	$(COMPOSE) logs -f --tail=100

down:
	$(COMPOSE) down -v

reset: down up
