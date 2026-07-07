FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg wget && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# prestart.sh को रन करने योग्य बनाएं और उसे चलाएँ
COPY prestart.sh .
RUN chmod +x prestart.sh
RUN ./prestart.sh

CMD ["python3", "main.py"]
