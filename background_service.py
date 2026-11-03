import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
LOG_FILE = PROJECT_DIR / "assistant.log"

# Fix stdout/stderr for pythonw (windowless execution)
try:
    log_fp = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
    sys.stdout = log_fp
    sys.stderr = log_fp
except Exception:
    pass

import io
import json
import time
import math
import asyncio
import winsound
import webbrowser
import subprocess
import threading
import tkinter as tk

import sounddevice as sd
import soundfile as sf
import numpy as np
from dotenv import load_dotenv
from pynput import keyboard

# Load environment
ENV_FILE = PROJECT_DIR / ".env"
load_dotenv(ENV_FILE)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print(" [x] Không tìm thấy GEMINI_API_KEY trong .env")
    sys.exit(1)

from google import genai
from google.genai import types

client = genai.Client(api_key=API_KEY)

SAMPLE_RATE = 16000
CHANNELS = 1

APP_PATHS = {
    "zalo": Path(r"C:\Users\anh58\AppData\Local\Programs\Zalo\Zalo.exe"),
    "chrome": Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    "discord": Path(r"C:\Users\anh58\AppData\Local\Discord\Update.exe"),
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "task_manager": "taskmgr.exe",
    "task manager": "taskmgr.exe",
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

def sound_start():
    try:
        winsound.Beep(900, 100)
        winsound.Beep(1200, 100)
    except Exception:
        pass

def sound_stop():
    try:
        winsound.Beep(1200, 80)
        winsound.Beep(900, 80)
    except Exception:
        pass

def sound_error():
    try:
        winsound.Beep(500, 200)
    except Exception:
        pass

# Initialize pygame mixer for TTS
try:
    import pygame
    pygame.mixer.init()
    AUDIO_PLAYBACK_AVAILABLE = True
except Exception:
    AUDIO_PLAYBACK_AVAILABLE = False

async def text_to_speech(text: str):
    if not text or not AUDIO_PLAYBACK_AVAILABLE:
        return
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice="vi-VN-HoaiMyNeural")
        temp_audio = PROJECT_DIR / "temp_tts.mp3"
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

# --- FLOATING VISUAL OVERLAY (VÒNG TRÒN / BANNER THÔNG BÁO) ---
class VoiceOverlay:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-alpha", 0.96)

        self.width = 380
        self.height = 76
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - self.width) // 2
        y = screen_h - self.height - 90  # 90px above taskbar
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg="#0f172a",
            highlightthickness=2,
            highlightbackground="#0ea5e9"
        )
        self.canvas.pack(fill="both", expand=True)

        self.anim_step = 0
        self.animating = False
        self.state = "hidden"
        self.root.withdraw()

    def show_listening(self):
        self.state = "listening"
        self.root.deiconify()
        self.canvas.config(highlightbackground="#06b6d4")  # Cyan neon
        self.animating = True
        self._animate_listening()

    def show_processing(self):
        self.state = "processing"
        self.animating = True
        self.canvas.config(highlightbackground="#a855f7")  # Purple neon
        self._animate_processing()

    def show_done(self, text, speech):
        self.state = "done"
        self.animating = False
        self.canvas.config(highlightbackground="#22c55e")  # Green
        self.canvas.delete("all")
        # Success icon
        self.canvas.create_oval(18, 18, 54, 54, fill="#22c55e", outline="")
        self.canvas.create_text(36, 36, text="✓", fill="#ffffff", font=("Segoe UI", 16, "bold"))
        # Text
        short_text = text if len(text) < 32 else text[:29] + "..."
        self.canvas.create_text(68, 26, anchor="w", text=f"\"{short_text}\"", fill="#f8fafc", font=("Segoe UI", 11, "bold"))
        short_speech = speech if len(speech) < 42 else speech[:39] + "..."
        self.canvas.create_text(68, 48, anchor="w", text=short_speech or "Đã thực thi thành công", fill="#86efac", font=("Segoe UI", 9))
        self.root.after(1800, self.hide)

    def show_error(self, message):
        self.state = "error"
        self.animating = False
        self.canvas.config(highlightbackground="#ef4444")  # Red
        self.canvas.delete("all")
        self.canvas.create_oval(18, 18, 54, 54, fill="#ef4444", outline="")
        self.canvas.create_text(36, 36, text="!", fill="#ffffff", font=("Segoe UI", 16, "bold"))
        self.canvas.create_text(68, 26, anchor="w", text="Chưa nghe rõ", fill="#f8fafc", font=("Segoe UI", 11, "bold"))
        self.canvas.create_text(68, 48, anchor="w", text=message, fill="#fca5a5", font=("Segoe UI", 9))
        self.root.after(1600, self.hide)

    def hide(self):
        self.state = "hidden"
        self.animating = False
        self.root.withdraw()

    def _animate_listening(self):
        if not self.animating or self.state != "listening":
            return
        self.canvas.delete("all")
        self.anim_step += 0.25

        # Pulsing circle effect
        r = 16 + 6 * math.sin(self.anim_step)
        # Outer ring
        self.canvas.create_oval(36 - r, 36 - r, 36 + r, 36 + r, outline="#06b6d4", width=2)
        # Center glow circle
        self.canvas.create_oval(23, 23, 49, 49, fill="#0284c7", outline="")
        self.canvas.create_text(36, 36, text="🎙️", font=("Segoe UI", 11))

        # Text labels
        self.canvas.create_text(68, 26, anchor="w", text="Đang lắng nghe...", fill="#f8fafc", font=("Segoe UI", 11, "bold"))
        self.canvas.create_text(68, 48, anchor="w", text="Hãy nói câu lệnh (hoặc dừng để AI chạy)", fill="#94a3b8", font=("Segoe UI", 9))
        self.root.after(45, self._animate_listening)

    def _animate_processing(self):
        if not self.animating or self.state != "processing":
            return
        self.canvas.delete("all")
        self.anim_step += 0.3

        # Spinning / Pulsing purple ring
        r = 15 + 4 * math.cos(self.anim_step)
        self.canvas.create_oval(36 - r, 36 - r, 36 + r, 36 + r, outline="#a855f7", width=2)
        self.canvas.create_oval(24, 24, 48, 48, fill="#7e22ce", outline="")
        self.canvas.create_text(36, 36, text="🧠", font=("Segoe UI", 10))

        # Text labels
        dots = "." * (int(self.anim_step * 2) % 4 + 1)
        self.canvas.create_text(68, 26, anchor="w", text=f"AI đang suy nghĩ{dots}", fill="#f8fafc", font=("Segoe UI", 11, "bold"))
        self.canvas.create_text(68, 48, anchor="w", text="Đang nhận diện giọng nói & phân tích", fill="#c084fc", font=("Segoe UI", 9))
        self.root.after(100, self._animate_processing)

overlay_app = None

def execute_action(action_data: dict):
    action = action_data.get("action", "chat")
    target = action_data.get("target", "").lower().strip()
    speech = action_data.get("speech_response", "")

    print(f"\n[{time.strftime('%H:%M:%S')}] Hành động: {action} | Mục tiêu: {target}")
    if speech:
        print(f"[{time.strftime('%H:%M:%S')}] Trợ lý: {speech}")
        threading.Thread(target=speak, args=(speech,), daemon=True).start()

    try:
        if action == "open_app":
            matched = False
            for app_key, app_val in APP_PATHS.items():
                if app_key in target or target in app_key:
                    matched = True
                    if isinstance(app_val, Path) and app_val.exists():
                        subprocess.Popen([str(app_val)])
                    else:
                        subprocess.Popen(str(app_val), shell=True)
                    break
            if not matched:
                subprocess.Popen(f"start {target}", shell=True)

        elif action == "search_web":
            search_url = f"https://www.google.com/search?q={target}"
            webbrowser.open(search_url)

        elif action == "open_url":
            if not target.startswith("http"):
                target = f"https://{target}"
            webbrowser.open(target)

        elif action == "system_control":
            if "lock" in target or "khóa" in target:
                subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
            elif "volume_up" in target:
                subprocess.run('powershell -c "(New-Object -ComObject Wscript.Shell).SendKeys([char]175 * 5)"', shell=True)
            elif "volume_down" in target:
                subprocess.run('powershell -c "(New-Object -ComObject Wscript.Shell).SendKeys([char]174 * 5)"', shell=True)
            elif "mute" in target:
                subprocess.run('powershell -c "(New-Object -ComObject Wscript.Shell).SendKeys([char]173)"', shell=True)

    except Exception as e:
        print(f" [!] Lỗi khi thực thi: {e}")

is_recording = False
stop_recording_event = threading.Event()

def record_and_process():
    global is_recording
    if is_recording:
        return
    is_recording = True
    stop_recording_event.clear()

    # Show overlay and play start sound
    if overlay_app:
        overlay_app.root.after(0, overlay_app.show_listening)
    sound_start()
    print(f"\n[{time.strftime('%H:%M:%S')}] Đang ghi âm giọng nói...")

    audio_frames = []
    chunk_size = 1024
    silence_threshold = 0.014
    silence_duration_needed = 1.3
    consecutive_silent_chunks = 0
    chunks_per_second = SAMPLE_RATE / chunk_size
    max_silent_chunks = int(silence_duration_needed * chunks_per_second)
    has_spoken = False
    start_time = time.time()
    max_duration = 10

    def callback(indata, frames, time_info, status):
        audio_frames.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", blocksize=chunk_size, callback=callback):
        while not stop_recording_event.is_set():
            time.sleep(0.04)
            if audio_frames:
                latest_chunk = audio_frames[-1]
                rms = np.sqrt(np.mean(latest_chunk**2))
                
                if rms > silence_threshold:
                    has_spoken = True
                    consecutive_silent_chunks = 0
                else:
                    if has_spoken:
                        consecutive_silent_chunks += 1
                        if consecutive_silent_chunks >= max_silent_chunks:
                            break

            if time.time() - start_time > max_duration:
                break

    sound_stop()
    is_recording = False

    if not audio_frames or not has_spoken:
        print(" [!] Không nhận thấy giọng nói.")
        if overlay_app:
            overlay_app.root.after(0, lambda: overlay_app.show_error("Vui lòng thử nói lại gần mic hơn"))
        return

    # Switch overlay to processing state
    if overlay_app:
        overlay_app.root.after(0, overlay_app.show_processing)

    audio_data = np.concatenate(audio_frames, axis=0)
    wav_io = io.BytesIO()
    sf.write(wav_io, audio_data, SAMPLE_RATE, format="WAV")
    wav_bytes = wav_io.getvalue()

    try:
        print(" [🧠 AI đang xử lý...]")
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav"),
                types.Part.from_text(text="Hãy nghe đoạn ghi âm và phân tích ý định theo định dạng JSON đã chỉ dẫn.")
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        res_text = response.text.strip()
        data = json.loads(res_text)
        transcription = data.get("transcription", "")
        speech = data.get("speech_response", "")

        print(f"[{time.strftime('%H:%M:%S')}] Bạn nói: \"{transcription}\"")

        # Show success on overlay
        if overlay_app:
            overlay_app.root.after(0, lambda: overlay_app.show_done(transcription, speech))

        execute_action(data)
    except Exception as e:
        print(f" [!] Lỗi AI: {e}")
        sound_error()
        if overlay_app:
            overlay_app.root.after(0, lambda: overlay_app.show_error(f"Lỗi: {e}"))

def on_hotkey_trigger():
    if not is_recording:
        threading.Thread(target=record_and_process, daemon=True).start()
    else:
        stop_recording_event.set()

def start_keyboard_listener():
    with keyboard.GlobalHotKeys({
        '<ctrl>+<shift>+<space>': on_hotkey_trigger,
        '<f8>': on_hotkey_trigger
    }) as h:
        h.join()

def main():
    global overlay_app
    print(f"[{time.strftime('%H:%M:%S')}] AI Voice Assistant with Visual Overlay đã khởi động thành công!")
    print(f"[{time.strftime('%H:%M:%S')}] Phím nóng: [Ctrl + Shift + Space] hoặc [F8]")

    # Start keyboard listener in daemon thread
    listener_thread = threading.Thread(target=start_keyboard_listener, daemon=True)
    listener_thread.start()

    # Main thread runs Tkinter event loop for the overlay widget
    root = tk.Tk()
    overlay_app = VoiceOverlay(root)
    root.mainloop()

if __name__ == "__main__":
    main()
