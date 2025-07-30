# Fintra

Fintra is a backend service for tracking personal finances. It provides a simple API for recording income and expense transactions and calculating account balance.

## Features

- Record income and expense transactions
- Track transaction details including amount, category, description, and party
- Query current balance
- Built-in monitoring with Prometheus and Grafana
- Database migrations with yoyo-migrations

## API Endpoints

- `POST /transaction` - Record a new transaction
- `GET /balance` - Get current account balance
- `GET /health` - Health check endpoint

## How to Run

### Prerequisites
- Docker and Docker Compose

### Running the Application

```bash
docker compose up --build -d
```

This will start:
- The Fintra application on port 8000
- A PostgreSQL database
- Prometheus monitoring on port 9090
- Grafana dashboards on port 3000 (user: admin, password: admin)

### Accessing the Application

- API: http://localhost:8000
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

## Running Tests

### Setup Test Environment

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install test dependencies:

```bash
pip install -r requirements/test.txt
```

3. Launch test services:

```bash
docker compose -f tests/compose.yaml up -d
```

4. Run database migrations:

```bash
./tests/run_migration.sh
```

### Run Tests

```bash
pytest -vv
```

## Development

### Project Structure

- `fintra/` - Main application code
- `alembic/` - Database migration scripts
- `tests/` - Test files
- `grafana/`, `prometheus/` - Monitoring configuration

### Adding New Dependencies

While in your virtual environment:

```bash
pip install <new dependency>
pip freeze > requirements/main.txt  # or the appropriate requirements file
```

### Working with Database Migrations

Create a new migration:
```bash
yoyo new -m "Add column to foo"
```

```bash
yoyo apply
```

### Debug Mode

To run the application in debug mode:

change compose.yaml - add port for debugging and change entrypoint to debug-entrypoint.sh
the app service should look like this:
```yaml
  app:
    build: .
    environment:
      LOG_LEVEL: warning
      DATABASE_URL: postgresql://user:pass@db:5432/main
    ports:
      - "8000:8000"
      - "8001:8001"
      - "5678:5678"
    depends_on:
      - db
    entrypoint:
      - ./debug-entrypoint.sh
```
now you can connect your remote debugger, e.g. to connect via neovim DAP, add this to dap.configurations.python table:
```lua
{
    type = "python",
    request = "attach",
    name = "Attach to a Docker container",
    connect = {
        host = "127.0.0.1",
        port = 5678,
    },
    pathMappings = {
        {
            localRoot = vim.fn.getcwd(),
            remoteRoot = "/app",
        },
    },
    justMyCode = false, -- set this to true if you want debugger to skip dependencies code
}
```



```bash
# Install debug requirements
pip install -r requirements/dev.txt

# Use the debug entrypoint
docker compose up --build -d app
```
This enables remote debugging on port 5678.

