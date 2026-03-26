import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class MixamoAPIClient:
    BASE_URL = "https://www.mixamo.com/api/v1"

    def __init__(self, token_file="mixamo_token.txt"):
        if not os.path.exists(token_file):
            raise FileNotFoundError(f"Bearer token not found at {token_file}")
        
        with open(token_file, "r") as f:
            self.token = f.read().strip()
            
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Api-Key": "mixamo2",
        }

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def request(self, method, url, **kwargs):
        headers = {**self.headers, **kwargs.pop("headers", {})}
        if not url.startswith("http"):
            url = f"{self.BASE_URL}/{url.lstrip('/')}"
            
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        
        if response.status_code == 204:
            return None
        return response.json()

    def upload_character(self, file_path):
        """
        Uploads a character FBX/OBJ/ZIP to Mixamo.
        Returns the character_id.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Character file not found: {file_path}")
            
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            # The API might require specific multipart structure. 
            # Based on standard Mixamo API, it's a POST to /characters
            result = self.request("POST", "characters", files=files)
            
        return result.get("character_id") or result.get("id")
