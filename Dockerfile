# ---- Stage 1: compile ----
FROM ubuntu:22.04 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc-9 libgomp1 libc6-dev git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Fork with the OpenMP thread-count fix (upstream PR prameshsingh/generalized-modularity-density#2)
ARG RENEEL_COMMIT=013f0db53d9b48b2bccdcc11e9724c28ba926873
RUN git clone https://github.com/sekunder/generalized-modularity-density.git /build \
 && git -C /build checkout ${RENEEL_COMMIT}
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
ENV PYTHONPATH=/app

WORKDIR /data
