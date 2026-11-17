FROM php:8.2-apache
COPY index.php /var/www/html/index.php
# route non-existent paths (like /api/assets/upload) to the front controller,
# while real files (the uploaded .php webshell) are served/executed directly
RUN printf '<Directory /var/www/html>\n  FallbackResource /index.php\n</Directory>\n' \
      > /etc/apache2/conf-enabled/fallback.conf \
 && mkdir -p /var/www/html/uploads && chmod 777 /var/www/html/uploads \
 && echo 'FLAG{cockpit_wildcard_upl0ad_w3bshell}' > /flag
