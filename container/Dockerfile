FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    && apt-get clean

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
COPY sqlshield.py /workspace/sqlshield.py
VOLUME ["/workspace/uploads", "/workspace/config"]

CMD ["python3"]


