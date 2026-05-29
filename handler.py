import os
import uuid
import tempfile
import requests
import runpod
import torch
import soundfile as sf
import boto3
from omnivoice import OmniVoice

MODEL_ID = os.getenv("OMNIVOICE_MODEL_ID", "k2-fsa/OmniVoice")
DEVICE = os.getenv("DEVICE", "cuda:0")
DTYPE = torch.float16 if "cuda" in DEVICE else torch.float32

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME") or os.getenv("R2_BUCKET")
R2_PUBLIC_BASE_URL = os.getenv("R2_PUBLIC_BASE_URL")

model = None


def load_model():
    global model
    if model is None:
        print(f"Loading OmniVoice model={MODEL_ID} device={DEVICE} dtype={DTYPE}...")
        model = OmniVoice.from_pretrained(MODEL_ID, device_map=DEVICE, dtype=DTYPE)
        print("OmniVoice model loaded.")
    return model


def download_file(url, path):
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)


def upload_to_r2(local_path, key, content_type="audio/wav"):
    missing = [k for k, v in {
        "R2_ACCOUNT_ID": R2_ACCOUNT_ID,
        "R2_ACCESS_KEY_ID": R2_ACCESS_KEY_ID,
        "R2_SECRET_ACCESS_KEY": R2_SECRET_ACCESS_KEY,
        "R2_BUCKET_NAME/R2_BUCKET": R2_BUCKET_NAME,
        "R2_PUBLIC_BASE_URL": R2_PUBLIC_BASE_URL,
    }.items() if not v]
    if missing:
        raise RuntimeError("Missing R2 env vars: " + ", ".join(missing))
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    )
    s3.upload_file(local_path, R2_BUCKET_NAME, key, ExtraArgs={"ContentType": content_type})
    return f"{R2_PUBLIC_BASE_URL.rstrip('/')}/{key}"


def synthesize(inp):
    job_id = inp.get("job_id") or f"audio_{uuid.uuid4().hex[:12]}"
    text = (inp.get("text") or inp.get("prompt") or "").strip()
    ref_audio_url = inp.get("ref_audio_url") or inp.get("reference_audio_url")
    ref_text = (inp.get("ref_text") or inp.get("reference_text") or "").strip()
    language = inp.get("language", "Vietnamese")
    num_step = int(inp.get("num_step", 16))
    speed = float(inp.get("speed", 1.0))
    user_id = (inp.get("user_id") or "anonymous").replace("@", "_").replace("/", "_")

    if not text:
        raise ValueError("Missing input.text")
    if not ref_audio_url:
        raise ValueError("Missing input.ref_audio_url")
    if not ref_text:
        raise ValueError("Missing input.ref_text / input.reference_text")

    m = load_model()
    with tempfile.TemporaryDirectory() as td:
        ref_path = os.path.join(td, "ref.wav")
        out_path = os.path.join(td, "out.wav")
        download_file(ref_audio_url, ref_path)
        audio = m.generate(
            text=text,
            ref_audio=ref_path,
            ref_text=ref_text,
            language=language,
            num_step=num_step,
            speed=speed,
        )
        sf.write(out_path, audio[0], 24000)
        r2_key = f"generated_audio/{user_id}/{job_id}.wav"
        audio_url = upload_to_r2(out_path, r2_key)
    return {
        "ok": True,
        "success": True,
        "job_id": job_id,
        "audio_url": audio_url,
        "sample_rate": 24000,
        "model": MODEL_ID,
        "engine": "omnivoice",
    }


def handler(job):
    inp = job.get("input", {}) or {}
    action = (inp.get("action") or inp.get("mode") or "text_to_audio").lower()
    if action in {"text_to_audio", "tts", "synthesize", "clone_tts"}:
        return synthesize(inp)
    if action == "health":
        return {"ok": True, "model": MODEL_ID, "device": DEVICE}
    raise ValueError(f"Unsupported action: {action}")


runpod.serverless.start({"handler": handler})
