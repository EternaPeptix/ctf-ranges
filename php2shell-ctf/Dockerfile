FROM php:8.5.11-apache
WORKDIR /var/www/html
COPY ./app/ /var/www/html/
COPY ./app/docker-php-flags.ini /usr/local/etc/php/conf.d/zz-flags.ini
COPY ./boot.sh /usr/local/bin/boot.sh
RUN chmod +x /usr/local/bin/boot.sh
EXPOSE 80
HEALTHCHECK --interval=5s --timeout=2s --retries=3 CMD php -r 'exit(0);' || exit 1
CMD ["/usr/local/bin/boot.sh"]