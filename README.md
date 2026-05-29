# FlozenAI Voice Backend - Clone Voice + Text To Audio

## Logic vận hành

- GPT voice: Frontend → Cloudflare Worker → RunPod → OpenAI `gpt-4o-mini-tts` → upload audio lên R2.
- Voice public / voice clone: Frontend → Cloudflare Worker → RunPod → OmniVoice → upload audio lên R2.
- Cloudflare Worker tạo `job_id`, lưu trạng thái vào bảng `jobs`, frontend poll `/api/job/:job_id` giống các luồng video cũ.
- Vì đây là luồng audio, Worker vẫn lưu URL audio vào cột `result_video_url` để tái sử dụng dashboard/status hiện tại, đồng thời trả thêm `result_audio_url` và `audio_url`.

## ENV RunPod bắt buộc

```env
OPENAI_API_KEY=sk-xxxx
OPENAI_TTS_MODEL=gpt-4o-mini-tts

R2_ACCOUNT_ID=xxxx
R2_ACCESS_KEY_ID=xxxx
R2_SECRET_ACCESS_KEY=xxxx
R2_BUCKET_NAME=flozenai-videos
R2_PUBLIC_BASE_URL=https://pub-93764efb31b244babb2bc41d8cb399bb.r2.dev
```

## ENV RunPod khuyến nghị

```env
OMNIVOICE_MODEL_ID=k2-fsa/OmniVoice
DEVICE=cuda:0
```

## Test GPT TTS trực tiếp RunPod

```json
{
  "input": {
    "action": "openai_tts",
    "job_id": "test_gpt_tts_001",
    "user_id": "test_user",
    "text": "Xin chào, đây là bản thử nghiệm giọng GPT 4o mini TTS trên RunPod.",
    "voice": "nova",
    "openai_tts_model": "gpt-4o-mini-tts",
    "response_format": "wav"
  }
}
```

## Test OmniVoice trực tiếp RunPod

```json
{
  "input": {
    "action": "text_to_audio",
    "job_id": "test_omnivoice_001",
    "user_id": "test_user",
    "text": "Đây là nội dung cần tạo audio mới bằng giọng mẫu.",
    "ref_audio_url": "https://pub-93764efb31b244babb2bc41d8cb399bb.r2.dev/Voice_publich_template/vi/omnivoice_south_male_young_neutral.wav",
    "ref_text": "chuẩn bị tiến tới kỷ năm 20 năm hoạt động trong ngành thủy sản với khát vọng nâng tầm tôm việt và mục tiêu giá trị 1 tỷ đô",
    "language": "Vietnamese",
    "num_step": 16,
    "speed": 1
  }
}
```

## ENV Cloudflare Worker

```env
RUNPOD_OMNIVOICE_ENDPOINT_URL=https://api.runpod.ai/v2/xxxxx/run
RUNPOD_OMNIVOICE_API_KEY=xxxxx
R2_PUBLIC_BASE_URL=https://pub-93764efb31b244babb2bc41d8cb399bb.r2.dev
MAX_VOICE_SAMPLE_MB=30
OMNIVOICE_DEFAULT_NUM_STEP=16
```

Bindings:
- `DB` = D1 đang dùng cho bảng `jobs`
- `R2_BUCKET` = bucket `flozenai-videos`

> Không cần `OPENAI_API_KEY` trên Cloudflare Worker. Key OpenAI phải set trên RunPod.
