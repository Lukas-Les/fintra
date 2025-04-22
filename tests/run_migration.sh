# Generate SQL without executing
DATABASE_URL="postgresql://testuser:testpass@localhost:2222/test_db" alembic upgrade head --sql > migration.sql

# Review and then apply
PGPASSWORD=testpass psql -h localhost -p 2222 -U testuser -d test_db -f migration.sql
