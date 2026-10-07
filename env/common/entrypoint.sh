#!/bin/bash
# Entrypoint shared by the nacre images.
# As root (RunPod): install PUBLIC_KEY for root and the nacre user, expose the
# container environment to ssh sessions, and start sshd on 22/tcp.
# As any other user (HPC, CI smoke tests): skip sshd and run the command.
set -e

if [ "$(id -u)" = "0" ]; then
    install -d -m 700 /root/.ssh /home/nacre/.ssh
    if [ -n "${PUBLIC_KEY:-}" ]; then
        printf '%s\n' "$PUBLIC_KEY" | tee /root/.ssh/authorized_keys /home/nacre/.ssh/authorized_keys >/dev/null
    fi
    chmod 600 /root/.ssh/authorized_keys /home/nacre/.ssh/authorized_keys 2>/dev/null || true
    chown -R nacre:nacre /home/nacre/.ssh

    # ssh sessions do not inherit the container environment; replay it at login.
    printenv | grep -vE '^(PUBLIC_KEY|_|SHLVL|PWD|OLDPWD|HOME|USER|LOGNAME|SHELL|TERM|HOSTNAME)=' \
        | sed 's/\\/\\\\/g; s/"/\\"/g; s/^\([^=]*\)=\(.*\)$/export \1="\2"/' > /etc/nacre_environment
    echo 'for f in /etc/nacre_environment; do [ -r "$f" ] && . "$f"; done' > /etc/profile.d/nacre_environment.sh

    mkdir -p /run/sshd
    ssh-keygen -A >/dev/null
    /usr/sbin/sshd
fi

if [ "$#" -gt 0 ]; then
    exec "$@"
fi
exec sleep infinity
