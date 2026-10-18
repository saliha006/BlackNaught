FROM registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest
COPY requirements-app.txt requirements-test.txt constraints-image.txt /tmp/
# -c pins everything the image already ships, so pip can never replace its compiled s390x stack
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements-app.txt -c /tmp/constraints-image.txt \
 && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements-test.txt -c /tmp/constraints-image.txt
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["/opt/venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
