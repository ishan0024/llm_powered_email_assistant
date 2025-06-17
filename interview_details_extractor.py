from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

class InterviewDetailsExtractor:
    def __init__(self, model_name="gpt-3.5-turbo", temperature=0):
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.prompt = PromptTemplate(
            input_variables=["subject", "body", "ocr_text"],
            template="""
Extract the following info from this email: interview date, interview time, recruiter name, company name.
If info is missing, respond with null values.

Email:
Subject: {subject}
Body: {body}
OCR Text: {ocr_text}

Respond only with JSON like:
{{
  "interview_date": "YYYY-MM-DD" or null,
  "interview_time": "HH:MM" or null,
  "recruiter_name": string or null,
  "company_name": string or null
}}
            """,
        )
        self.chain = self.prompt | self.llm | JsonOutputParser()

    def extract(self, subject, body, ocr_text):
        return self.chain.invoke({
            "subject": subject,
            "body": body,
            "ocr_text": ocr_text or ""
        })