FROM python:3.11

# Install poetry
RUN pip install --no-cache-dir poetry==1.6.1

# Set working directory
WORKDIR /app

# Copy source code
COPY . /app

# Setup dependencies
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

# Set entrypoint
ENTRYPOINT ["poetry", "run", "python", "src/bot.py"]




