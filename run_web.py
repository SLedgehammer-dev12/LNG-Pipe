#!/usr/bin/env python3
"""Launcher for LNG Pipeline Flow Simulator."""

import subprocess
import sys

if __name__ == "__main__":
    print("❄️ LNG Boru Akışı Termo-Hidrolik Simülatörü başlatılıyor...")
    cmd = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nUygulama sonlandırıldı.")
