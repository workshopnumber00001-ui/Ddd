FROM python:3.11-slim

WORKDIR /app

# ffmpeg और wget इंस्टॉल (Videos/PDFs डाउनलोड के लिए जरूरी)
RUN apt-get update && apt-get install -y ffmpeg wget && rm -rf /var/lib/apt/lists/*

# Requirements इंस्टॉल करें
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# पूरा प्रोजेक्ट कॉपी करें
COPY . .

# बॉट को रन करें
CMD ["python3", "main.py"]
