# ============================================================================
#  orrery -- control
#    make up      build + start the service (http://localhost:9500)
#    make check   run the reference solver in-network; exit 0 iff token recovered
#    make down    stop + remove everything
#    make reset   down + up (fresh polynomial, fresh token, full budget)
#
#  The service hands out 32 evaluations per gear train and the reference solver
#  needs all 32. A correct submission winds a fresh gear train with a full
#  budget, so `make check` is green however often it is run.
# ============================================================================
COMPOSE = docker compose
.PHONY: up check down reset

up:
	$(COMPOSE) up -d --build --wait

check:
	./scripts/verify.sh

down:
	$(COMPOSE) down -v

reset:
	$(COMPOSE) down -v
	$(COMPOSE) up -d --build --wait
