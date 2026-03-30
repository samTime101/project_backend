FROM python:3.12-slim

RUN apt-get update
RUN apt-get install -y build-essential
RUN rm -rf /var/lib/apt/lists/*


WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY ./ ./

EXPOSE 8000
WORKDIR /app
CMD ["sh", "-c", "python manage.py runserver 0.0.0.0:8000"]