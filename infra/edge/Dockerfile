FROM debian:trixie-slim
# trixie's nginx links OpenSSL 3.5, which is what offers the X25519MLKEM768 post-quantum key exchange.
RUN apt-get update && apt-get install -y --no-install-recommends nginx curl && rm -rf /var/lib/apt/lists/*
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 8443
CMD ["nginx", "-g", "daemon off;"]
