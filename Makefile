.PHONY: seed
seed:
	python -m scripts.seed

.PHONY: seed-catalog
seed-catalog:
	python -m scripts.seed_catalog

.PHONY: superuser
superuser:
	python -m scripts.create_superuser

.PHONY: wait-db
wait-db:
	python -m scripts.wait_for_db