# Everlight Ventures Makefile
# Convenient shortcuts for common development tasks

.PHONY: help install dev build clean setup db-push db-migrate db-seed db-studio test lint

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	npm install

dev: ## Start development server
	npm run dev

build: ## Build for production
	npm run build

clean: ## Clean build artifacts and dependencies
	npm run clean

setup: ## Run initial setup (install, generate, env)
	bash scripts/setup.sh

db-generate: ## Generate Prisma client
	npm run db:generate

db-push: ## Push Prisma schema to database (dev)
	npm run db:push

db-migrate: ## Run database migrations (production)
	npm run db:migrate

db-seed: ## Seed database with demo data
	cd packages/db && npm run seed

db-studio: ## Open Prisma Studio
	npm run db:studio

db-reset: ## Reset database (WARNING: destroys all data)
	cd packages/db && npx prisma migrate reset --force

test: ## Run tests
	npm run test

lint: ## Lint all packages
	npm run lint

docker-up: ## Start Docker services (PostgreSQL)
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-reset: ## Reset Docker volumes (WARNING: destroys all data)
	docker-compose down -v

health: ## Check application health
	@echo "Checking health endpoint..."
	@curl -s http://localhost:3000/api/health | jq || echo "Server not running or jq not installed"

logs: ## Tail development logs
	npm run dev 2>&1 | tee dev.log
