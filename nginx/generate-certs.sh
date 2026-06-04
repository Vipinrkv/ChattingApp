#!/bin/sh

CERT_DIR=/etc/nginx/ssl
mkdir -p "$CERT_DIR"

if [ -f "$CERT_DIR/tls.crt" ] && [ -f "$CERT_DIR/tls.key" ]; then
  echo "SSL certificate already exists"
  exit 0
fi

openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout "$CERT_DIR/tls.key" \
  -out "$CERT_DIR/tls.crt" \
  -subj "/CN=localhost"

echo "Generated self-signed certificate"
