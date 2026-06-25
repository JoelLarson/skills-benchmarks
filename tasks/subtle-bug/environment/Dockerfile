FROM docker.io/library/ubuntu:24.04
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && pip3 install --no-cache-dir --break-system-packages pytest==8.4.1
COPY solution.py /root/solution.py
WORKDIR /root
