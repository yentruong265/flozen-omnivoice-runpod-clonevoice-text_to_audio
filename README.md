# FlozenAI OmniVoice Voice Backend READY

Endpoint này dùng cho 2 luồng mới:

1. `Clone voice – Nhân bản giọng`: Cloudflare Worker lưu audio mẫu + reference text + voice_id vào R2/D1. Nếu có `test_text`, Worker gọi RunPod endpoint này để tạo audio test.
2. `Text to audio`: Worker gọi endpoint này khi user chọn voice clone hoặc voice public R2.

## Env trên RunPod

```env
OMNIVOICE_MODEL_ID=k2-fsa/OmniVoice
DEVICE=cuda:0
R2_ACCOUNT_ID=xxx
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_BUCKET_NAME=flozenai-videos
R2_PUBLIC_BASE_URL=https://pub-93764efb31b244babb2bc41d8cb399bb.r2.dev
```

## JSON test trực tiếp RunPod

```json
{
  "input": {
    "action": "text_to_audio",
    "job_id": "omnivoice_yen_vi_test_001",
    "user_id": "test_user",
    "text": "Đây là nội dung cần tạo audio mới bằng giọng mẫu.",
    "ref_audio_url": "https://pub-93764efb31b244babb2bc41d8cb399bb.r2.dev/Voice_publich_template/vi/omnivoice_south_male_young_neutral.wav",
    "ref_text": "Dán đúng reference text của audio mẫu tại đây.",
    "language": "Vietnamese",
    "num_step": 16,
    "speed": 1
  }
}
```

> Lưu ý: với voice public R2, bạn cần lưu/reference text chuẩn cho từng mẫu trong Worker/D1. Nếu để trống, OmniVoice sẽ báo thiếu `ref_text`.
