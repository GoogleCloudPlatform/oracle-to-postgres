FROM python:3.8.0-slim

RUN pip install --upgrade pip
RUN pip install google-apitools
RUN pip install absl-py

COPY runner.py .
COPY cloud_datastream_resource_manager.py .
COPY datastream datastream/

ENTRYPOINT ["python", "runner.py"]
