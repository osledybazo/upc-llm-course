FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY static ./static
EXPOSE 6661
# 0.0.0.0 = listen on every interface inside the container, so the host's port mapping can reach it
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "6661"]
