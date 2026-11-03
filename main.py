import os
import sys

# Ensure UTF-8 output in Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import io
import json
import time
import asyncio
import webbrowser
import subprocess
import threading
from pathlib import Path
import sounddevice as sd
import soundfile as sf
import numpy as np
from dotenv import load_dotenv

# Load environment variables
ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(ENV_FILE)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("=" * 60)
    print(" [!] CHƯA CÓ GEMINI_API_KEY TRONG FILE .env")
    print("=" * 60)
    key_input = input("👉 Nhập hoặc dán GEMINI_API_KEY vào đây (Enter để tiếp tục): ").strip()
    if key_input:
        API_KEY = key_input
        with open(ENV_FILE, "a", encoding="utf-8") as f:
            f.write(f"\nGEMINI_API_KEY={API_KEY}\n")
        print(" [✓] Đã lưu API Key vào file .env!")
    else:
        print(" [x] Không có API Key, chương trình không thể kết nối AI.")
        sys.exit(1)

from google import genai
from google.genai import types

client = genai.Client(api_key=API_KEY)

# Audio recording configuration
SAMPLE_RATE = 16000  # 16kHz is optimal for speech recognition
CHANNELS = 1

# Known Windows app paths on this PC
APP_PATHS = {
    "zalo": Path(r"C:\Users\anh58\AppData\Local\Programs\Zalo\Zalo.exe"),
    "chrome": Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    "discord": Path(r"C:\Users\anh58\AppData\Local\Discord\Update.exe"),
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "task_manager": "taskmgr.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "valorant": Path(r"C:\Riot Games\VALORANT\live\ShooterGame\Binaries\Win64\VALORANT-Win64-Shipping.exe"),
    "tiktok_live": Path(r"C:\Program Files\TikTok LIVE Studio\0.95.8\TikTok LIVE Studio.exe")
}

SYSTEM_INSTRUCTION = """
Bạn là trợ lý ảo AI thông minh điều khiển máy tính Windows bằng giọng nói của người dùng tiếng Việt.
Bạn sẽ nhận được 1 đoạn ghi âm giọng nói từ người dùng.
Nhiệm vụ của bạn:
1. Nghe và chuyển âm thanh thành văn bản tiếng Việt chính xác (transcription).
2. Hiểu ý định của người dùng và chọn hành động (action) phù hợp nhất.
3. Trả về DUY NHẤT một chuỗi JSON hợp lệ với cấu trúc sau (không kèm markdown ```json):
{
  "transcription": "nội dung người dùng vừa nói",
  "action": "open_app | search_web | open_url | system_control | chat",
  "target": "tên ứng dụng (zalo, chrome, discord, notepad...) hoặc từ khóa tìm kiếm hoặc lệnh",
  "speech_response": "câu trả lời ngắn gọn, tự nhiên bằng tiếng Việt để đọc lại cho người dùng nghe (dưới 15 từ)"
}

Quy tắc hành động (action):
- "open_app": Người dùng muốn mở ứng dụng (zalo, chrome, discord, notepad, máy tính, valorant, v.v.)
- "search_web": Người dùng muốn tìm kiếm cái gì đó (tìm kiếm Google, tìm thời tiết, tin tức...)
- "open_url": Người dùng muốn vào 1 trang web cụ thể (youtube, facebook, github...)
- "system_control": Tác vụ hệ thống như: "lock" (khóa máy), "volume_up", "volume_down", "mute"
- "chat": Người dùng hỏi thông tin thông thường hoặc trò chuyện, trả lời ngắn gọn qua speech_response.
"""

# Initialize audio playback (pygame mixer)
try:
    import pygame
    pygame.mixer.init()
    AUDIO_PLAYBACK_AVAILABLE = True
except Exception:
    AUDIO_PLAYBACK_AVAILABLE = False

async def text_to_speech(text: str):
    """Speaks text using Edge-TTS with natural Vietnamese voice"""
    if not text or not AUDIO_PLAYBACK_AVAILABLE:
        return
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice="vi-VN-HoaiMyNeural")
        temp_audio = Path(__file__).parent / "temp_tts.mp3"
        await communicate.save(str(temp_audio))
        
        pygame.mixer.music.load(str(temp_audio))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()
        if temp_audio.exists():
            temp_audio.unlink(missing_ok=True)
    except Exception as e:
        print(f" [!] TTS Error: {e}")

def speak(text: str):
    asyncio.run(text_to_speech(text))

def execute_action(action_data: dict):
    """Executes the interpreted action on Windows"""
    action = action_data.get("action", "chat")
    target = action_data.get("target", "").lower().strip()
    speech = action_data.get("speech_response", "")

    print(f"\n [⚡] Hành động: {action} | Mục tiêu: {target}")
    if speech:
        print(f" [🤖 Trợ lý]: {speech}")
        # Speak in a background thread so execution is fast
        threading.Thread(target=speak, args=(speech,), daemon=True).start()

    try:
        if action == "open_app":
            matched = False
            for app_key, app_val in APP_PATHS.items():
                if app_key in target or target in app_key:
                    matched = True
                    if isinstance(app_val, Path) and app_val.exists():
                        subprocess.Popen([str(app_val)])
                        print(f" [✓] Đã khởi chạy: {app_val}")
                    else:
                        subprocess.Popen(str(app_val), shell=True)
                        print(f" [✓] Đã mở: {app_key}")
                    break
            
            if not matched:
                subprocess.Popen(f"start {target}", shell=True)
                print(f" [✓] Đã gửi lệnh mở: {target}")

        elif action == "search_web":
            search_url = f"https://www.google.com/search?q={target}"
            webbrowser.open(search_url)
            print(f" [✓] Đang tìm kiếm trên Google: {target}")

        elif action == "open_url":
            if not target.startswith("http"):
                target = f"https://{target}"
            webbrowser.open(target)
            print(f" [✓] Đang mở trang: {target}")

        elif action == "system_control":
            if "lock" in target or "khóa" in target:
                subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
                print(" [✓] Đã khóa màn hình máy tính.")
            elif "volume_up" in target:
                subprocess.run('powershell -c "(New-Object -ComObject Wscript.Shell).SendKeys([char]175 * 5)"', shell=True)
                print(" [✓] Đã tăng âm lượng.")
            elif "volume_down" in target:
                subprocess.run('powershell -c "(New-Object -ComObject Wscript.Shell).SendKeys([char]174 * 5)"', shell=True)
                print(" [✓] Đã giảm âm lượng.")
            elif "mute" in target:
                subprocess.run('powershell -c "(New-Object -ComObject Wscript.Shell).SendKeys([char]173)"', shell=True)
                print(" [✓] Đã bật/tắt tiếng.")

    except Exception as e:
        print(f" [!] Lỗi khi thực thi lệnh: {e}")

def record_audio_until_keypress():
    """Records audio from default mic until Enter is pressed"""
    print("\n [🎙️ Đang ghi âm...] Hãy nói câu lệnh của bạn (Nhấn ENTER để kết thúc nói): ", end="", flush=True)
    audio_frames = []
    recording = True

    def callback(indata, frames, time_info, status):
        if recording:
            audio_frames.append(indata.copy())

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", callback=callback)
    with stream:
        input()
        recording = False

    if not audio_frames:
        return None

    audio_data = np.concatenate(audio_frames, axis=0)
    wav_io = io.BytesIO()
    sf.write(wav_io, audio_data, SAMPLE_RATE, format="WAV")
    return wav_io.getvalue()

def process_voice_command(wav_bytes: bytes):
    """Sends audio to Gemini 3.5 Flash for instant transcription and intent reasoning"""
    print(" [🧠 AI đang xử lý giọng nói...]")
    start_time = time.time()

    # Try models in order of speed
    models_to_try = ["gemini-3.5-flash", "gemini-3.8-flash"]
    response = None

    for m in models_to_try:
        try:
            response = client.models.generate_content(
                model=m,
                contents=[
                    types.Part.from_bytes(
                        data=wav_bytes,
                        mime_type="audio/wav"
                    ),
                    types.Part.from_text(
                        text="Hãy nghe đoạn ghi âm và phân tích ý định theo định dạng JSON đã chỉ dẫn."
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            if response:
                break
        except Exception:
            continue

    if not response:
        print(" [!] Không nhận được phản hồi từ AI. Hãy thử lại.")
        return

    try:
        elapsed = time.time() - start_time
        res_text = response.text.strip()
        data = json.loads(res_text)

        print(f" [⚡ Xong trong {elapsed:.2f}s]")
        print(f" [🗣️ Bạn nói]: \"{data.get('transcription', '')}\"")
        execute_action(data)

    except Exception as e:
        print(f" [!] Lỗi khi đọc kết quả AI: {e}")

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║             AI VOICE ASSISTANT (TRỢ LÝ GIỌNG NÓI)          ║
║      Điều khiển máy tính Windows bằng giọng nói tiếng Việt ║
╚════════════════════════════════════════════════════════════╝
* Micro đang dùng: Microphone (Realtek(R) Audio) tích hợp
* Model AI: Google Gemini 3.5 Flash (Siêu tốc)
* Giọng đọc phản hồi: Microsoft Hoài My (Neural)

👉 HƯỚNG DẪN DÙNG:
- Nhấn ENTER để BẮT ĐẦU NÓI.
- Nói xong câu lệnh thì nhấn ENTER LẦN NỮA.
- Gõ 'q' rồi ENTER để thoát.
    """)

    while True:
        try:
            choice = input("\n👉 Nhấn [ENTER] để bắt đầu nói (hoặc 'q' để thoát): ").strip()
            if choice.lower() == 'q':
                print("Tạm biệt bạn!")
                break
            
            wav_bytes = record_audio_until_keypress()
            if wav_bytes and len(wav_bytes) > 2000:
                process_voice_command(wav_bytes)
            else:
                print(" [!] Không thu được âm thanh (quá ngắn). Thử lại nhé.")
        except KeyboardInterrupt:
            print("\nĐã dừng chương trình.")
            break
        except Exception as e:
            print(f"Lỗi: {e}")

if __name__ == "__main__":
    main()
