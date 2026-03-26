import os
import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    def get_product(self, anim_id, character_id):
        url = f"products/{anim_id}?similar=0&character_id={character_id}"
        return self.request("GET", url)

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

    def _download_file(self, url, output_path):
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    def _process_single_animation(self, character_id, anim, output_dir):
        anim_id = anim["id"]
        anim_name = anim["name"]
        filename = f"{anim_name}_{character_id}.fbx"
        output_path = os.path.join(output_dir, filename)
        
        if os.path.exists(output_path):
            return True
            
        product_data = self.get_product(anim_id, character_id)
        gms_hash = product_data["details"]["gms_hash"]
        
        # Format gms_hash params if they are lists (as in mixamo_harvester.py)
        if isinstance(gms_hash.get("params"), list):
             gms_hash["params"] = ",".join(str(param[1]) for param in gms_hash["params"])

        self.export_animation(character_id, [gms_hash], anim_name)
        download_url = self.monitor_export_progress(character_id)
        self._download_file(download_url, output_path)
        return True

    def download_animations(self, character_id, animations, output_dir, max_workers=5, progress_callback=None):
        """
        Concurrent download of animations.
        """
        os.makedirs(output_dir, exist_ok=True)
        results = {}
        total = len(animations)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_anim = {
                executor.submit(self._process_single_animation, character_id, anim, output_dir): anim 
                for anim in animations
            }
            
            completed = 0
            for future in as_completed(future_to_anim):
                anim = future_to_anim[future]
                anim_id = anim["id"]
                try:
                    results[anim_id] = future.result()
                except Exception as e:
                    print(f"Error processing animation {anim['name']}: {e}")
                    results[anim_id] = False
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total, anim["name"])
                    
        return results
