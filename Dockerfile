FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:1

# 기본 패키지 설치
RUN apt-get update && apt-get install -y \
    python3.9 \
    python3-pip \
    xvfb \
    wget \
    git \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
RUN pip3 install --no-cache-dir \
    numpy \
    torch \
    transformers \
    ai2thor==2.1.0 \
    anthropic \
    openai \
    google-generativeai \
    gym \
    hydra-core \
    revtok \
    vocab \
    opencv-python \
    Pillow \
    scipy \
    scikit-image \
    progressbar2 \
    tqdm

WORKDIR /app

# Xvfb 자동 시작 스크립트
RUN echo '#!/bin/bash\n\
Xvfb :1 -screen 0 1024x768x24 -ac +extension GLX &\n\
sleep 3\n\
export DISPLAY=:1\n\
exec "$@"' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash"]

