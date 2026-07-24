import os
import sys
import subprocess

if __name__ == "__main__":
    print("🚀 Launching Master AI Server on Hugging Face Spaces...")
    # Set default port to 7860 as expected by HF
    os.environ["PORT"] = "7860"
    os.environ["MASTERAI_PORT"] = "7860"
    # Execute server.py directly
    sys.exit(subprocess.call([sys.executable, "server.py"]))
