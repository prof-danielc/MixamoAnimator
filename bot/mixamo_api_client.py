import os
import requests
import json
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class MixamoAPIClient:
    BASE_URL = "https://www.mixamo.com/api/v1"

    def __init__(self, token_file="mixamo_token.txt", catalog_file="animations_catalog.json"):
        if not os.path.exists(token_file):
            raise FileNotFoundError(f"Bearer token not found at {token_file}")
        
        with open(token_file, "r") as f:
            self.token = f.read().strip()
            
        self.catalog_file = catalog_file
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
            result = self.request("POST", "characters", files=files)
            
        return result.get("character_id") or result.get("id")

    def fetch_animation_catalog(self, limit=100, force_refresh=False):
        """
        Fetches the animation catalog from Mixamo API and caches it locally.
        Returns a list of animation objects.
        """
        if not force_refresh and os.path.exists(self.catalog_file):
            with open(self.catalog_file, "r") as f:
                return json.load(f)

        animations = []
        page = 1
        while len(animations) < limit:
            url = f"products?page={page}&limit=96&order=&type=Motion%2CMotionPack&query="
            data = self.request("GET", url)
            results = data.get("results", [])
            if not results:
                break
            
            animations.extend(results)
            if len(results) < 96:
                break
            page += 1

        animations = animations[:limit]
        with open(self.catalog_file, "w") as f:
            json.dump(animations, f)

        return animations

    def export_animation(self, character_id, gms_hash_array, product_name):
        """
        Triggers an animation export for a specific character.
        """
        url = "animations/export"
        payload = {
            "character_id": character_id,
            "gms_hash": gms_hash_array,
            "preferences": {"format": "fbx7", "skin": "false", "fps": "30", "reducekf": "0"},
            "product_name": product_name,
            "type": "Motion"
        }
        result = self.request("POST", url, json=payload)
        return result.get("job_id")

    def monitor_export_progress(self, character_id, interval=5):
        """
        Polls the character monitor endpoint until the export is completed.
        Returns the job_result (download URL).
        """
        url = f"characters/{character_id}/monitor"
        while True:
            data = self.request("GET", url)
            status = data.get("status")
            
            if status == "completed":
                return data.get("job_result")
            elif status == "failed":
                raise Exception(f"Export failed: {data.get('message', 'Unknown error')}")
            
            time.sleep(interval)
