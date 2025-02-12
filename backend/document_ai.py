from dotenv import load_dotenv
import os
import base64
import requests
import json
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from secret_key import google_credentials

class Document_AI:
    def __init__(self):
        google_credentials()
        load_dotenv()
        self.project_id = os.getenv("PROJECT_ID")
        self.location = os.getenv("LOCATION")
        self.processor_id = os.getenv("PROCESSOR_ID")
        self.service_account_path = google_credentials()
        
    def auth_session(self):
        credentials = service_account.Credentials.from_service_account_file(
            self.service_account_path, 
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        authed_session = AuthorizedSession(credentials)
        return authed_session
    
    def process_document(self, file_data: bytes):
        encoded_content = base64.b64encode(file_data).decode("utf-8")
        
        payload = {
            "rawDocument": {
                "content": encoded_content,
                "mimeType": "application/pdf"
            }
        }
        
        endpoint = (
            f"https://{self.location}-documentai.googleapis.com/v1/projects/"
            f"{self.project_id}/locations/{self.location}/processors/"
            f"{self.processor_id}:process"
        )
        
        session = self.auth_session()
        response = session.post(endpoint, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("document", {}).get("text", "")
        else:
            print(f"Error: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response text: {response.text}")
            return None