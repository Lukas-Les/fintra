# Use a specific Python version with Debian Bookworm
FROM python:3.13.1-bookworm

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first for better caching
COPY requirements.txt .

# Create a virtual environment and install dependencies
RUN python -m venv .venv && \
    . .venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code after dependencies are installed
COPY fintra/ /app

# Expose the application port
EXPOSE 8000

# Set the virtual environment as the default for the container
ENV PATH="/app/.venv/bin:$PATH"

# Command to run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
