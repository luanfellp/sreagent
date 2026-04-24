FROM python:3.11-slim
WORKDIR /app
COPY app.py /app/app.py
RUN pip install prometheus-client flask
EXPOSE 8001
CMD ["python", "app.py"]
