FROM php:8.2-apache
COPY index.php /var/www/html/index.php
# the "chroot" the renderer is meant to stay inside, and the sibling dir that
# its flawed strpos()-prefix check accidentally also admits:
RUN mkdir -p /var/www/html-secret \
 && echo 'FLAG{dompdf_strp0s_chr00t_byp4ss_lfi}' > /var/www/html-secret/flag.txt \
 && echo 'company logo placeholder' > /var/www/html/logo.txt
