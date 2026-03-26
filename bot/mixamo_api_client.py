import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class MixamoAPIClient:
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
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        
        if response.status_code == 204:
            return None
        return response.json()
