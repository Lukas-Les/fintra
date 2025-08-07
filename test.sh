#!/bin/bash
docker compose -f tests/compose.yaml up -d
pytest -vv
docker compose -f tests/compose.yaml down
