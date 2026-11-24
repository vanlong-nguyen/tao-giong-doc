# Web tạo giọng đọc (Text-to-Speech) - chạy local
# Cài:  pip install flask edge-tts
# Chạy: python app.py  -> mở http://127.0.0.1:5000

import asyncio
import io

import edge_tts
from flask import Flask, render_template_string, request, send_file

app = Flask(__name__)

DEFAULT_VOICE = "vi-VN-HoaiMyNeural"
FALLBACK_VOICES = [
    {"ShortName": "vi-VN-HoaiMyNeural", "Locale": "vi-VN", "Gender": "Female"},
    {"ShortName": "vi-VN-NamMinhNeural", "Locale": "vi-VN", "Gender": "Male"},
    {"ShortName": "ja-JP-NanamiNeural", "Locale": "ja-JP", "Gender": "Female"},
    {"ShortName": "ja-JP-KeitaNeural", "Locale": "ja-JP", "Gender": "Male"},
    {"ShortName": "en-US-AriaNeural", "Locale": "en-US", "Gender": "Female"},
    {"ShortName": "en-US-GuyNeural", "Locale": "en-US", "Gender": "Male"},
]


def load_voices():
    """Lấy toàn bộ giọng edge-tts có (~400 giọng, 140+ ngôn ngữ). Mất mạng thì dùng list dự phòng."""
    try:
        voices = asyncio.run(edge_tts.list_voices())
    except Exception:
        voices = FALLBACK_VOICES
    # {locale: [(shortname, nhãn), ...]}
    grouped = {}
    for v in sorted(voices, key=lambda x: (x["Locale"], x["ShortName"])):
        name = v["ShortName"].split("-", 2)[-1].replace("Neural", "")
        gender = "nữ" if v["Gender"] == "Female" else "nam"
        grouped.setdefault(v["Locale"], []).append((v["ShortName"], f"{name} ({gender})"))
    return grouped


VOICES = load_voices()
VOICE_IDS = {sn for lst in VOICES.values() for sn, _ in lst}

HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>Tạo giọng đọc</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 760px; margin: 40px auto; padding: 0 16px; }
  textarea { width: 100%; height: 260px; font-size: 16px; padding: 10px; box-sizing: border-box; }
  .row { display: flex; gap: 16px; align-items: center; margin: 12px 0; flex-wrap: wrap; }
  button { padding: 10px 24px; font-size: 16px; cursor: pointer; }
  #status { color: #666; }
  audio { width: 100%; margin-top: 12px; }
</style>
</head>
<body>
  <h1>Tạo giọng đọc</h1>
  <textarea id="text" placeholder="Dán văn bản vào đây..."></textarea>
  <div class="row">
    <label>Ngôn ngữ: <select id="locale"></select></label>
    <label>Giọng: <select id="voice"></select></label>
  </div>
  <div class="row">
    <label>Tốc độ: <input id="rate" type="range" min="-50" max="50" value="0">
      <span id="rateVal">0%</span></label>
    <label>Cao độ: <input id="pitch" type="range" min="-50" max="50" value="0">
      <span id="pitchVal">0Hz</span></label>
  </div>
  <div class="row">
    <button id="go">Tạo giọng</button>
    <span id="status"></span>
  </div>
  <audio id="player" controls hidden></audio>
  <div><a id="dl" download="giong_doc.mp3" hidden>Tải MP3</a></div>

<script>
const $ = id => document.getElementById(id);
const VOICES = {{ voices|tojson }};
const fillVoices = () => {
  $('voice').innerHTML = VOICES[$('locale').value]
    .map(([id, label]) => `<option value="${id}">${label}</option>`).join('');
};
$('locale').innerHTML = Object.keys(VOICES)
  .map(l => `<option value="${l}">${l}</option>`).join('');
$('locale').value = VOICES['vi-VN'] ? 'vi-VN' : Object.keys(VOICES)[0];
$('locale').onchange = fillVoices;
fillVoices();
$('rate').oninput = () => $('rateVal').textContent = $('rate').value + '%';
$('pitch').oninput = () => $('pitchVal').textContent = $('pitch').value + 'Hz';
$('go').onclick = async () => {
  const text = $('text').value.trim();
  if (!text) { $('status').textContent = 'Chưa có chữ.'; return; }
  $('go').disabled = true; $('status').textContent = 'Đang tạo...';
  try {
    const fd = new FormData();
    fd.append('text', text); fd.append('voice', $('voice').value); fd.append('rate', $('rate').value); fd.append('pitch', $('pitch').value);
    const res = await fetch('/tts', { method: 'POST', body: fd });
    if (!res.ok) throw new Error(await res.text());
    const url = URL.createObjectURL(await res.blob());
    $('player').src = url; $('player').hidden = false; $('player').play();
    $('dl').href = url; $('dl').hidden = false;
    $('status').textContent = 'Xong.';
  } catch (e) {
    $('status').textContent = 'Lỗi: ' + e.message;
  } finally {
    $('go').disabled = false;
  }
};
</script>
</body>
</html>
"""


async def synthesize(text: str, voice: str, rate: str, pitch: str) -> io.BytesIO:
    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf


@app.get("/")
def index():
    return render_template_string(HTML, voices=VOICES)


@app.post("/tts")
def tts():
    text = request.form.get("text", "").strip()
    if not text:
        return "Thiếu văn bản", 400
    voice = request.form.get("voice", DEFAULT_VOICE)
    if voice not in VOICE_IDS:
        voice = DEFAULT_VOICE

    def clamp(key):
        try:
            return max(-50, min(50, int(request.form.get(key, 0))))
        except ValueError:
            return 0

    try:
        audio = asyncio.run(
            synthesize(text, voice, f"{clamp('rate'):+d}%", f"{clamp('pitch'):+d}Hz")
        )
    except Exception as e:  # mất mạng, dịch vụ đổi API...
        return f"Không tạo được giọng: {e}", 500
    return send_file(audio, mimetype="audio/mpeg", download_name="giong_doc.mp3")


if __name__ == "__main__":
    app.run(debug=True)
