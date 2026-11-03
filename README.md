# 🎙️ Windows AI Voice Assistant (Trợ lý Giọng nói Tiếng Việt)

Trợ lý ảo điều khiển máy tính Windows bằng giọng nói tiếng Việt sử dụng mô hình đa phương thức **Google Gemini 2.0 Flash** và phản hồi âm thanh bằng **Microsoft Neural TTS**.

---

## ✨ Tính năng nổi bật
* **Nhận diện & Xử lý siêu tốc (< 0.5s)**: Gửi thẳng âm thanh giọng nói tiếng Việt lên Gemini 2.0 Flash để vừa nhận diện chữ vừa phân tích ý định trong một lượt gọi duy nhất.
* **Tự động điều khiển ứng dụng Windows**:
  * Mở các ứng dụng phổ biến: Zalo, Chrome, Discord, Valorant, Notepad, Task Manager, Calculator, v.v.
  * Tìm kiếm Google và mở trang web theo yêu cầu.
  * Điều khiển hệ thống: Khóa máy tính (`lock`), tăng/giảm âm lượng, bật/tắt tiếng (`mute`).
* **Phản hồi bằng giọng đọc tự nhiên**: Trả lời bằng giọng tiếng Việt truyền cảm qua Microsoft Edge-TTS (`vi-VN-HoaiMyNeural`).
* **Hỗ trợ tối ưu âm thanh**: Tối ưu thu âm trực tiếp qua micro tích hợp của laptop hoặc micro rời.

---

## 🚀 Cài đặt & Khởi chạy

### Yêu cầu:
* Hệ điều hành: Windows 10 / 11
* Python 3.11+ (hoặc trình quản lý gói [uv](https://github.com/astral-sh/uv))

### 1. Cài đặt thư viện:
Nếu dùng `uv` (khuyên dùng):
```bash
uv sync
```
Hoặc dùng `pip`:
```bash
pip install -r requirements.txt
```

### 2. Cấu hình API Key:
1. Lấy API Key miễn phí tại [Google AI Studio](https://aistudio.google.com/apikey).
2. Tạo file `.env` từ `.env.example` và dán key của bạn:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Chạy chương trình:
Nhấp đúp chuột vào file:
```text
run.bat
```
hoặc chạy bằng dòng lệnh:
```bash
uv run python main.py
```

---

## 🎯 Cách sử dụng:
1. Nhấn phím **`ENTER`** để bắt đầu nói.
2. Nói câu lệnh tiếng Việt tự nhiên (Ví dụ: *"Mở Zalo cho tôi"*, *"Tìm thời tiết Hà Nội hôm nay"*, *"Khóa màn hình máy tính"*).
3. Nhấn **`ENTER`** lần nữa để kết thúc câu nói.
4. AI sẽ lập tức thực thi hành động và trả lời bạn bằng giọng nói.
