FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential \
    libopenblas-dev \
    libffi-dev \
    libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install popular data science libraries
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    numpy \
    pandas \
    scipy \
    scikit-learn \
    matplotlib \
    seaborn \
    jupyter \
    ipython \
    torch \
    torchvision \
    torchaudio \
    tensorflow \
    notebook

WORKDIR /workspace
COPY terno.py /workspace/terno.py

VOLUME ["/workspace/uploads", "/workspace/config"]

CMD ["python3"]
