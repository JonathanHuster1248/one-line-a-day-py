FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

# Install prerequisites
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Copy project
COPY . .

# Install the newest Python version satisfying requires-python
RUN uv python install

# Create a virtual environment using that interpreter
RUN uv venv

# Install the package into the virtual environment
RUN uv pip install --python .venv/bin/python . 

EXPOSE 8000

CMD ["uv", "run", "-m", "one_line_day_py.main"]