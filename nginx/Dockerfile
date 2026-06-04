FROM nginx:stable-alpine

RUN apk add --no-cache openssl

COPY default.conf /etc/nginx/conf.d/default.conf
COPY generate-certs.sh /usr/local/bin/generate-certs.sh
RUN chmod +x /usr/local/bin/generate-certs.sh

CMD ["/bin/sh", "-c", "/usr/local/bin/generate-certs.sh && nginx -g 'daemon off;' "]
