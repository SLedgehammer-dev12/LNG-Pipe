#!/usr/bin/env python3
"""Launcher for LNG Pipeline Flow Simulator."""

import subprocess
import sys

if __name__ == "__main__":
    print("❄️ LNG Boru Akışı Termo-Hidrolik Simülatörü başlatılıyor...")
    port = sys.argv[1] if len(sys.argv) > 1 else "8502"
    cmd = [sys.executable, "-m", "streamlit", "run", "app.py", f"--server.port={port}", "--server.headless=true"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nUygulama sonlandırıldı.")
