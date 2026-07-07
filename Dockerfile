FROM python:3.11-slim

WORKDIR /app

# ffmpeg और wget इंस्टॉल
RUN apt-get update && apt-get install -y ffmpeg wget && rm -rf /var/lib/apt/lists/*

# Requirements install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# बाकी सारा कोड कॉपी करें
COPY . .

# prestart.sh को executable बनाएं और चलाएँ
COPY prestart.sh .
RUN chmod +x prestart.sh
RUN ./prestart.sh

# बॉट शुरू करें
CMD ["python3", "main.py"]
