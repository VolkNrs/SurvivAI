#If there is no AI model


import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

MODEL_URL = "https://huggingface.co/sitsope/phi-3-mini-4k-instruct-q4/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / "phi-3-mini-4k-instruct-q4.gguf"
REQUIREMENTS_PATH = Path("requirements.txt")


def install_requirements() -> None:
    if not REQUIREMENTS_PATH.exists():
        print("requirements.txt not found. Skipping dependency install.")
        return

    print("Installing Python dependencies from requirements.txt...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)])


def download_model() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 0:
        print(f"Model already exists: {MODEL_PATH}")
        return

    print(f"Downloading model to {MODEL_PATH}...")
    with urlopen(MODEL_URL) as response, MODEL_PATH.open("wb") as out_file:
        total = response.headers.get("Content-Length")
        total_size = int(total) if total else 0
        downloaded = 0
        chunk_size = 1024 * 1024

        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break

            out_file.write(chunk)
            downloaded += len(chunk)

            if total_size > 0:
                percent = (downloaded / total_size) * 100
                print(f"Downloaded {downloaded / (1024 * 1024):.1f} MB / {total_size / (1024 * 1024):.1f} MB ({percent:.1f}%)", end="\r")
            else:
                print(f"Downloaded {downloaded / (1024 * 1024):.1f} MB", end="\r")

    print("\nModel download complete.")


def main() -> None:
    print("Starting SurvivAI setup...")
    install_requirements()
    download_model()
    print("Setup complete. You can now run: flet run main.py")


if __name__ == "__main__":
    main()
