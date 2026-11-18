.PHONY: up check down reset
up:
	docker compose up -d --build
check:
	./scripts/verify.sh
down:
	docker compose down -v
reset: down up