import json
from typing import Optional
from pydantic import PrivateAttr
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool


class EmailClassifierChain:
    def __init__(self, model_name: str = "gpt-3.5-turbo", temperature: float = 0.7):
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.prompt = PromptTemplate(
            input_variables=["subject", "body", "ocr_text"],
            template="""
You are a smart email classifier.

Classify the following email into one of the following categories:
- JOB: Job offers, interview calls, recruiter emails
- SPAM: Promotions, sales, scams, irrelevant emails
- PERSONAL: Friends, family, personal conversations
- OTHER: System notifications, newsletters, etc.

Only respond with: JOB, SPAM, PERSONAL, or OTHER.

Email:
Subject: {subject}
Body: {body}
OCR Text: {ocr_text}
"""
        )
        self.chain = self.prompt | self.llm | StrOutputParser()

    def classify(self, subject: str, body: str, ocr_text: str) -> str:
        return self.chain.invoke({
            "subject": subject,
            "body": body.strip(),
            "ocr_text": ocr_text or ""
        })


class EmailClassifierTool(BaseTool):
    name: str = "email_classifier"
    description: str = "Classifies an email as JOB, SPAM, PERSONAL, or OTHER."

    _classifier: EmailClassifierChain = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use object.__setattr__ to bypass pydantic validation here
        object.__setattr__(self, "_classifier", EmailClassifierChain())

    def _run(self, input_str: str, run_manager: Optional[object] = None) -> str:
        email = json.loads(input_str)
        return self._classifier.classify(
            email.get("subject", ""),
            email.get("body", ""),
            email.get("ocr_text", "")
        )