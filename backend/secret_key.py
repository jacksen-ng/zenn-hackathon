from google.cloud import secretmanager
import os

def get_secret(secret_name):
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "zenn-hackathon1")
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def env_file():
    env_data = get_secret("env-file")
    with open(".env", "w") as f:
        f.write(env_data)
    return ".env"
    
def google_credentials():
    credentials_data = get_secret("google-credentials1")
    with open("zenn-hackathon1-a5002f68a40d.json", "w") as f:
        f.write(credentials_data)
    return "zenn-hackathon1-a5002f68a40d.json"