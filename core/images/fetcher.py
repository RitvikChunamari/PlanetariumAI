import os
import requests
import urllib.parse
import json
import uuid

class NasaImageFetcher:
    def __init__(self, cache_dir="cache/images"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def fetch_image(self, query: str):
        # 1. Check if we already have a cached result for this exact query
        # Since queries might differ slightly, we could hash them, but for simplicity we'll just query the API.
        
        search_url = f"https://images-api.nasa.gov/search?q={urllib.parse.quote(query)}&media_type=image"
        try:
            resp = requests.get(search_url, timeout=3.0)
            resp.raise_for_status()
            data = resp.json()
            
            items = data.get("collection", {}).get("items", [])
            if not items:
                return None
                
            first_item = items[0]
            metadata = first_item.get("data", [{}])[0]
            links = first_item.get("links", [])
            
            if not links:
                return None
                
            # Usually ~thumb.jpg. Let's try to get ~medium.jpg
            image_url = links[0].get("href", "")
            original_url = image_url
            if image_url.endswith("~thumb.jpg"):
                image_url = image_url.replace("~thumb.jpg", "~orig.jpg")
                
            title = metadata.get("title", "Unknown Title")
            description = metadata.get("description", "")
            date_created = metadata.get("date_created", "")
            center = metadata.get("center", "NASA")
            
            # Generate a local filename
            filename = f"{uuid.uuid4().hex}.jpg"
            local_path = os.path.join(self.cache_dir, filename)
            
            # Download the image
            try:
                img_resp = requests.get(image_url, timeout=3.0)
                img_resp.raise_for_status()
            except requests.exceptions.RequestException:
                # Fallback to thumb
                img_resp = requests.get(original_url, timeout=3.0)
                img_resp.raise_for_status()
                
            with open(local_path, "wb") as f:
                f.write(img_resp.content)
                
            return {
                "local_path": f"/images/{filename}", # URL path for the frontend
                "title": title,
                "description": description[:300] + "..." if len(description) > 300 else description,
                "date": date_created,
                "source": center
            }
            
        except Exception as e:
            print(f"NASA Image API error: {e}")
            return None
