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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts").strip()

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
        region_name="auto",
    )
    s3.upload_file(local_path, R2_BUCKET_NAME, key, ExtraArgs={"ContentType": content_type})
    return f"{R2_PUBLIC_BASE_URL.rstrip('/')}/{key}"


def safe_user_id(value):
    return str(value or "anonymous").replace("@", "_").replace("/", "_").replace("\\", "_").strip() or "anonymous"


def synthesize_omnivoice(inp):
    job_id = inp.get("job_id") or f"audio_{uuid.uuid4().hex[:12]}"
    text = (inp.get("text") or inp.get("prompt") or "").strip()
    ref_audio_url = inp.get("ref_audio_url") or inp.get("reference_audio_url")
    ref_text = (inp.get("ref_text") or inp.get("reference_text") or "").strip()
    language = inp.get("language", "Vietnamese")
    language_id = (inp.get("language_id") or inp.get("lang_id") or "").strip()
    num_step = int(inp.get("num_step", 16))
    speed = float(inp.get("speed", 1.0))
    user_id = safe_user_id(inp.get("user_email") or inp.get("user_id"))

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
        generate_kwargs = {
            "text": text,
            "ref_audio": ref_path,
            "ref_text": ref_text,
            "num_step": num_step,
            "speed": speed,
        }
        # OmniVoice official batch format uses language_id; older local installs may accept language.
        if language_id:
            generate_kwargs["language_id"] = language_id
        else:
            generate_kwargs["language"] = language
        try:
            audio = m.generate(**generate_kwargs)
        except TypeError:
            generate_kwargs.pop("language_id", None)
            generate_kwargs["language"] = language
            audio = m.generate(**generate_kwargs)
        sf.write(out_path, audio[0], 24000)
        r2_key = f"generated_audio/{user_id}/{job_id}.wav"
        audio_url = upload_to_r2(out_path, r2_key, content_type="audio/wav")
    return {
        "ok": True,
        "success": True,
        "job_id": job_id,
        "audio_url": audio_url,
        "audio_key": r2_key,
        "sample_rate": 24000,
        "model": MODEL_ID,
        "engine": "omnivoice",
        "language": language,
        "language_id": language_id or "",
    }


def synthesize_openai_tts(inp):
    job_id = inp.get("job_id") or f"audio_gpt_{uuid.uuid4().hex[:12]}"
    text = (inp.get("text") or inp.get("prompt") or "").strip()
    voice = (inp.get("voice") or "nova").strip()
    model_name = (inp.get("openai_tts_model") or inp.get("model") or OPENAI_TTS_MODEL or "gpt-4o-mini-tts").strip()
    response_format = (inp.get("response_format") or "wav").strip().lower()
    user_id = safe_user_id(inp.get("user_email") or inp.get("user_id"))

    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY on RunPod OmniVoice endpoint")
    if not text:
        raise ValueError("Missing input.text")

    # Keep GPT TTS inside RunPod, same architecture as the older working FlozenAI video pipeline.
    res = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_name,
            "voice": voice,
            "input": text,
            "response_format": response_format,
        },
        timeout=180,
    )
    if not res.ok:
        raise RuntimeError(f"OpenAI TTS failed from RunPod: status={res.status_code}, body={res.text[:1000]}")

    ext = "mp3" if response_format == "mp3" else "wav"
    content_type = "audio/mpeg" if ext == "mp3" else "audio/wav"
    with tempfile.TemporaryDirectory() as td:
        out_path = os.path.join(td, f"out.{ext}")
        with open(out_path, "wb") as f:
            f.write(res.content)
        r2_key = f"generated_audio/{user_id}/{job_id}.{ext}"
        audio_url = upload_to_r2(out_path, r2_key, content_type=content_type)

    return {
        "ok": True,
        "success": True,
        "job_id": job_id,
        "audio_url": audio_url,
        "audio_key": r2_key,
        "model": model_name,
        "voice": voice,
        "engine": "openai_tts_runpod",
    }


def handler(job):
    inp = job.get("input", {}) or {}
    action = (inp.get("action") or inp.get("mode") or "text_to_audio").lower()
    if action in {"openai_tts", "gpt_tts", "gpt4o_tts", "gpt_4o_mini_tts"}:
        return synthesize_openai_tts(inp)
    if action in {"text_to_audio", "tts", "synthesize", "clone_tts"}:
        return synthesize_omnivoice(inp)
    if action == "health":
        return {"ok": True, "model": MODEL_ID, "device": DEVICE, "openai_tts_model": OPENAI_TTS_MODEL, "openai_key_set": bool(OPENAI_API_KEY)}
    raise ValueError(f"Unsupported action: {action}")


runpod.serverless.start({"handler": handler})
