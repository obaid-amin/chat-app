FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN apt-get update && apt-get install -y \
    python3-tk \
    tk \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

COPY . .
    
# Install dependencies if needed
 RUN pip install -r requirements.txt

 

# Default command (can be overridden)
CMD ["python", "server.py"]
