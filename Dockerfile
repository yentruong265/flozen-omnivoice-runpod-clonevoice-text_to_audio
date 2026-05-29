FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/workspace/hf_cache
ENV TRANSFORMERS_CACHE=/workspace/hf_cache
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

RUN apt-get update && apt-get install -y \
    python3.10 python3-pip ffmpeg git curl libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN python3.10 -m pip install --upgrade pip
RUN pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 \
    --extra-index-url https://download.pytorch.org/whl/cu128

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY handler.py /app/handler.py
CMD ["python3.10", "-u", "handler.py"]
