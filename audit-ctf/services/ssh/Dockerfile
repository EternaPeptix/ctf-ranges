FROM alpine:3.20
# C4 — "The Backdoor Key": a developer's passphrase-less SSH private key was left
# in the app's exposed backup directory (C3). It authenticates `dbadmin` here, so
# anyone who grabs the key gets a shell and the flag.
RUN apk add --no-cache openssh-server openssh-keygen && \
    adduser -D -s /bin/sh dbadmin && \
    echo 'dbadmin:dbadmin' | chpasswd && \
    ssh-keygen -A && \
    mkdir -p /home/dbadmin/.ssh && \
    printf 'AUD{ssh_l34k3d_pr1v4t3_k3y_dbadm1n_f00th0ld}\n' > /flag && chmod 644 /flag
COPY authorized_keys /home/dbadmin/.ssh/authorized_keys
RUN chown -R dbadmin:dbadmin /home/dbadmin/.ssh && \
    chmod 700 /home/dbadmin/.ssh && chmod 600 /home/dbadmin/.ssh/authorized_keys && \
    printf 'PubkeyAuthentication yes\nPasswordAuthentication no\nPermitRootLogin no\n' \
      >> /etc/ssh/sshd_config
EXPOSE 22
CMD ["/usr/sbin/sshd", "-D", "-e"]
