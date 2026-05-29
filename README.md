# FlozenAI Voice Backend - GPT TTS via RunPod FIXED

Bản này sửa lỗi OpenAI `unsupported_country_region_territory` khi Cloudflare Worker gọi thẳng OpenAI TTS.

## Logic mới nè

- User chọn voice GPT: Cloudflare Worker gọi RunPod với `action: "openai_tts"`; RunPod gọi `gpt-4o-mini-tts` và upload audio lên R2.
- User chọn voice public/clone: Cloudflare Worker gọi RunPod với `action: "text_to_audio"`; RunPod dùng OmniVoice và upload audio lên R2.

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
