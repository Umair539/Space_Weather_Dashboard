FROM python:3.11-slim

WORKDIR /app

COPY docker/app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/utils/logging_utils.py src/utils/logging_utils.py
COPY app/ app/
COPY .streamlit/ .streamlit/

EXPOSE 8501

CMD ["streamlit", "run", "app/run_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
