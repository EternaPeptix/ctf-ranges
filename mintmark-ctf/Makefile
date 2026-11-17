# ============================================================================
#  mintmark -- control
#    make up      build + start the service (http://localhost:9100)
#    make check   run the reference solver in-network; exit 0 iff token recovered
#    make down    stop + remove everything
#    make reset   down + up (fresh register, fresh sealed value, fresh token)
# ============================================================================
COMPOSE = docker compose
.PHONY: up check down reset

up:
	$(COMPOSE) up -d --build

check:
	./scripts/verify.sh

down:
	$(COMPOSE) down -v

reset:
	$(COMPOSE) down -v
	$(COMPOSE) up -d --build
