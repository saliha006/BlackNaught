FROM python:3.13-slim-trixie AS signer
# The base image has OpenSSL 3.5's library (ML-DSA) but not the openssl command the signer runs.
RUN apt-get update && apt-get install -y --no-install-recommends openssl && rm -rf /var/lib/apt/lists/*
# uid 1000 is linux1 on the VM, so the signer can read its owner-only key file from secrets/.
RUN useradd --uid 1000 --no-create-home --shell /usr/sbin/nologin signer
WORKDIR /srv
COPY signer.py .
USER signer
EXPOSE 8100
CMD ["python", "signer.py"]

FROM signer AS test
USER root
RUN pip install --no-cache-dir pytest==9.1.1 pytest-cov==7.1.0 coverage==7.16.2
COPY tests tests
USER signer
# /srv isn't writable by the signer user, so coverage data goes to /tmp and pytest's cache is off.
ENV COVERAGE_FILE=/tmp/.coverage
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--cov=signer", "--cov-report=term-missing", "tests"]
