# Tạo giọng đọc

Web tạo giọng đọc (text-to-speech) chạy trên máy, dùng edge-tts (miễn phí, ~400 giọng, 100+ ngôn ngữ). Xuất MP3.

## Chạy (Windows)
Cần Python 3.9+. Bấm đúp `run.bat`, hoặc:

```
pip install -r requirements.txt
python app.py
```
Mở http://127.0.0.1:5000

## Lưu ý
- Cần internet (edge-tts gọi dịch vụ đọc của Microsoft Edge).
- edge-tts không phải API chính thức, có thể ngừng chạy nếu Microsoft thay đổi.
