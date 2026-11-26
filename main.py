"""Griductive Solver: bấm Run (hoặc `python main.py`) để mở game trên trình duyệt.

    python main.py                 # chạy server GUI rồi tự mở trình duyệt
    python main.py --port 9000     # chọn cổng khác (tự đổi cổng nếu cổng đang bận)
    python main.py --no-browser    # chỉ chạy server, không tự mở trình duyệt

Dừng server bằng Ctrl+C trong terminal. Puzzle theo ngày được tạo ngầm khi server chạy
(lần đầu ~5 phút cho đủ 183 ngày; puzzle hôm nay có trước), lưu ở puzzles/daily/.
"""
from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))          # chạy được từ bất kỳ thư mục nào (vd: nút Run của VSCode)
for _s in (sys.stdout, sys.stderr):    # console Windows (cp1252) không in được tiếng Việt -> crash
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from src.engine.gui_server import DAILY, Handler  # noqa: E402


def bind(host: str, port: int, tries: int = 20) -> ThreadingHTTPServer:
    """Mở server ở `port`; nếu cổng đang bận thì thử cổng kế tiếp."""
    last = None
    for p in range(port, port + tries):
        try:
            return ThreadingHTTPServer((host, p), Handler)
        except OSError as e:
            last = e
    raise SystemExit(f"Không mở được cổng nào từ {port} đến {port + tries - 1}: {last}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Chạy Griductive Solver GUI")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--no-browser", action="store_true", help="không tự mở trình duyệt")
    a = ap.parse_args()

    server = bind(a.host, a.port)
    url = f"http://{a.host}:{server.server_address[1]}"
    print(f"Griductive GUI đang chạy tại {url}  (Ctrl+C để dừng)", flush=True)
    DAILY.warm_up()   # chạy nền: xoá puzzle quá 183 ngày, tạo puzzle hôm nay rồi lấp các ngày còn thiếu
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()