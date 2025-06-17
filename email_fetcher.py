from typing import Any, List, Dict, Optional
from langchain_core.tools import BaseTool
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract
import base64
from io import BytesIO


class EmailFetcherTool(BaseTool):
    name = "email_fetcher"
    description = "Fetches the latest emails from your Gmail inbox using the Gmail API."

    service: Any  # Gmail API service instance
    max_results: int = 5
    max_body_chars: int = 1000  # truncate body
    max_subject_chars: int = 200  # truncate subject
    max_ocr_chars: int = 500  # truncate OCR text

    def _truncate(self, text: str, max_len: int) -> str:
        if not text:
            return ""
        return text if len(text) <= max_len else text[:max_len] + "..."

    def _extract_body(self, parts: List[Dict[str, Any]]) -> str:
        body = ''
        for part in parts:
            if part.get('mimeType') == 'text/plain' and part['body'].get('data'):
                data = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                body += data
            elif part.get('mimeType') == 'text/html' and part['body'].get('data'):
                data = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                soup = BeautifulSoup(data, 'html.parser')
                body += soup.get_text()
        return body

    def _extract_images(self, parts: List[Dict[str, Any]]) -> List[bytes]:
        images = []
        for part in parts:
            if 'image' in part.get('mimeType', ''):
                data = part['body'].get('data')
                if data:
                    images.append(base64.urlsafe_b64decode(data))
            if part.get('parts'):
                images.extend(self._extract_images(part['parts']))
        return images

    def _ocr_images(self, image_bytes_list: List[bytes]) -> List[str]:
        texts = []
        for img_bytes in image_bytes_list:
            try:
                image = Image.open(BytesIO(img_bytes))
                text = pytesseract.image_to_string(image)
                texts.append(text.strip())
            except Exception as e:
                texts.append(f"[OCR error: {e}]")
        return texts

    def _run(self, max_results: int = None, run_manager: Optional[object] = None) -> List[Dict[str, str]]:
        max_results = max_results or self.max_results
        results = (
            self.service.users()
            .messages()
            .list(userId="me", maxResults=max_results)
            .execute()
        )
        messages = results.get('messages', [])
        email_data = []

        for msg in messages:
            msg_data = self.service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            payload = msg_data.get('payload', {})
            headers = payload.get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')

            parts = payload.get('parts', [])
            body = self._extract_body(parts)
            images = self._extract_images(parts)
            ocr_texts = self._ocr_images(images)

            # Truncate
            subject = self._truncate(subject, self.max_subject_chars)
            body = self._truncate(body, self.max_body_chars)
            ocr_text = self._truncate(" ".join(ocr_texts), self.max_ocr_chars) if ocr_texts else ""

            email_data.append({
                "id": msg['id'],
                "subject": subject,
                "body": body.strip(),
                "ocr_text": ocr_text
            })

        return email_data