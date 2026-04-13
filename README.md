🛡️ SurvivAI
Offline-First AI Emergency Assistant

SurvivAI is a lightweight, mobile-optimized survival assistant that runs a Large Language Model (LLM) entirely on your device. No internet, no APIs, and no tracking—just critical guidance when you are off the grid.

🚀 Key Features
100% Offline: Runs locally using a quantized Phi-3 Mini model.

RAG-Enhanced: Uses a local SQLite "Knowledge Vault" to ground AI responses in verified survival data.

Emergency Mode: Automatically detects high-risk scenarios to prioritize immediate life-saving actions.

Dynamic Theming: Clean UI built with Flet, supporting multiple themes for high-visibility or low-light situations.

Auto-Provisioning: Automatically handles model downloading and environment setup on the first run.

🛠️ Tech Stack
Language: Python 3.10+

AI Engine: llama-cpp-python (Phi-3-mini-4k-instruct-q4)

UI Framework: Flet (Flutter-based for Python)

Database: SQLite3

Async: asyncio for non-blocking AI streaming

📦 Installation & Setup
Clone the repository

Bash
git clone https://github.com/yourusername/SurvivAI.git
cd SurvivAI
Install Dependencies

Bash
pip install -r requirements.txt
Run the App

Bash
python main.py
Note: On the first launch, the app will automatically download the ~2.3GB model file. Ensure you have a stable connection for this step.

📂 Project Structure
main.py: The Flet GUI and application logic.

aiengine.py: Handles LLM initialization, prompt engineering, and regex sanitization.

survival_data.db: The SQLite vault containing verified guides and tags.

models/: Directory where the GGUF model is stored locally.

⚠️ Disclaimer
SurvivAI is a supplemental tool. While it uses verified data, it is not a replacement for professional medical advice or emergency services. Use at your own risk in survival situations.
