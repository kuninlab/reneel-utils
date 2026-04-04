# ---- Stage 1: compile ----
FROM ubuntu:22.04 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc-9 libgomp1 libc6-dev git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/prameshsingh/generalized-modularity-density.git /build
WORKDIR /build
RUN gcc-9 main.c help.c rg.c -fopenmp -lm -o reneel

# ---- Stage 2: runtime ----
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common gpg-agent libgomp1 \
 && add-apt-repository ppa:deadsnakes/ppa \
 && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-distutils \
 && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
 && update-alternatives --install /usr/bin/python  python  /usr/bin/python3.11 1

COPY --from=builder /build/reneel /app/reneel
RUN chmod +x /app/reneel

COPY reneelutil/ /app/reneelutil/

WORKDIR /data
