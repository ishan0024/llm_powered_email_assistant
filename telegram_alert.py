import json
import tempfile
import requests
from gtts import gTTS
from typing import Optional
from langchain_community.tools import BaseTool
from dotenv import load_dotenv


TELEGRAM_BOT_TOKEN = "7034853580:AAHnaYFQmp9JXouVXh_kr78CTncjXXrWdpc"
TELEGRAM_CHAT_ID = "6953638809"

class TelegramVoiceNoteTool(BaseTool):
    name: str = "telegram_voice_alert"
    description: str = "Sends a voice note alert on Telegram with interview details."

    def _run(self, input_str: str, run_manager: Optional[object] = None) -> str:
        data = json.loads(input_str)
        recruiter = data.get("recruiter_name", "Recruiter")
        company = data.get("company_name", "Company")
        date = data.get("interview_date", "unknown date")
        time = data.get("interview_time", "unknown time")

        message_text = (
            f"Hello! You have an interview scheduled with {recruiter} "
            f"from {company} on {date} at {time}."
        )

        tts = gTTS(text=message_text, lang='en')

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
            tts.save(tmp_path)

        with open(tmp_path, "rb") as voice_file:
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice",
                files={"voice": voice_file},
                data={"chat_id": TELEGRAM_CHAT_ID}
            )

        try:
            import os
            os.remove(tmp_path)
        except Exception as e:
            print(f"Warning: failed to delete temp file {tmp_path}. Error: {e}")

        if response.status_code == 200:
            return "Voice alert sent successfully."
        else:
            return f"Failed to send voice alert: {response.text}"

