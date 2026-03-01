FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for Matplotlib and Graphviz
RUN apt-get update && apt-get install -y \
    fonts-wqy-microhei \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure logs directory exists
RUN mkdir -p logs

EXPOSE 8501

# v1.3.5: Use tee to pipe ALL container output (including startup logs) to app.log
CMD ["sh", "-c", "streamlit run app.py --server.port=8501 --server.address=0.0.0.0 2>&1 | tee -a logs/app.log"]
