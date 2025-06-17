import json
import os
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType

from email_fetcher import EmailFetcherTool
from email_classifier import EmailClassifierTool
from telegram_alert import TelegramVoiceNoteTool  # your custom Telegram tool
from interview_details_extractor import InterviewDetailsExtractor  # your extractor
from gmail_utils import authenticate_gmail, move_to_spam
from email_tracker_db import EmailTrackerDB
from dotenv import load_dotenv
load_dotenv()


def main():

    # Authenticate Gmail API
    service = authenticate_gmail()

    # Initialize DB tracker
    db = EmailTrackerDB()

    # Initialize tools
    
    fetcher_tool = EmailFetcherTool(service=service, max_results=10)
    classifier_tool = EmailClassifierTool()
    telegram_tool = TelegramVoiceNoteTool()
    extractor = InterviewDetailsExtractor()

    tools = [
        Tool(name=fetcher_tool.name, func=fetcher_tool._run, description=fetcher_tool.description),
        Tool(name=classifier_tool.name, func=classifier_tool._run, description=classifier_tool.description),
        Tool(name=telegram_tool.name, func=telegram_tool._run, description=telegram_tool.description),
        Tool(
            name="move_to_spam",
            func=lambda msg_id: move_to_spam(service, msg_id),
            description="Moves an email by message ID to the Spam folder."
        ),
        Tool(
            name="db_mark_processed",
            func=lambda params: db.mark_processed(params['message_id'], params['subject'], params.get('sender', 'unknown')),
            description="Marks an email as processed in the DB. Expects dict with keys: message_id, subject, sender."
        ),
        Tool(
            name="db_mark_moved",
            func=lambda message_id: db.mark_moved(message_id),
            description="Marks an email as moved to spam in the DB. Expects the message ID."
        ),
        Tool(
            name="db_is_processed",
            func=lambda message_id: db.is_processed(message_id),
            description="Checks if an email message ID has been processed already. Returns True or False."
        )
    ]

    # Initialize LLM & Agent (optional, for reasoning or chaining)
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)

    # Fetch emails (call fetcher tool directly)
    emails = fetcher_tool._run()

    for email in emails:
        msg_id = email['id']

        # Skip if already processed
        if db.is_processed(msg_id):
            print(f"Skipping already processed email {msg_id}")
            continue

        # Classify email
        category = classifier_tool._run(json.dumps(email))
        print(f"Email {msg_id} classified as {category}")

        # Mark processed
        db.mark_processed(msg_id, email.get("subject", ""), email.get("sender", "unknown"))

        if category == "SPAM":
            print(f"Moving email {msg_id} to spam...")
            move_to_spam(service, msg_id)
            db.mark_moved(msg_id)

        elif category == "JOB":
            print("Extracting interview details...")

            try:
                extracted_data = extractor.extract(
                    subject=email.get("subject", ""),
                    body=email.get("body", ""),
                    ocr_text=email.get("ocr_text", "")
                )
                print("Extracted data:", extracted_data)

                print("Sending Telegram voice alert...")
                alert_resp = telegram_tool._run(json.dumps(extracted_data))
                print(alert_resp)

            except Exception as e:
                print(f"Failed to extract or alert: {e}")

    db.close()


if __name__ == "__main__":
    main()