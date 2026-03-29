# 1. Offizielles, leichtgewichtiges Python-Image als Basis
FROM python:3.11-slim

# 2. Arbeitsverzeichnis im Container festlegen
WORKDIR /app

# 3. Abhängigkeiten-Liste kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Deinen gesamten restlichen Code in den Container kopieren
COPY . .

# 5. Den Flask-Port für die interne Docker-Kommunikation freigeben
EXPOSE 5000

# 6. Startbefehl definieren (exakt passend zu deinem Dateinamen)
CMD ["python", "api_fetcher.py"]
