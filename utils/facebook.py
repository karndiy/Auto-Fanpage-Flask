import os, json, requests
from typing import Dict, Any, Optional

GRAPH = "https://graph.facebook.com/v24.0"

def load_settings(path: str = "settings.json") -> Dict[str, Any]:
  with open(path, "r", encoding="utf-8") as f:
    return json.load(f)

def save_settings(data: Dict[str, Any], path: str = "settings.json") -> None:
  with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

def debug_token(app_id: str, app_secret: str, token: str) -> Dict[str, Any]:
  url = f"{GRAPH}/debug_token"
  params = {"input_token": token, "access_token": f"{app_id}|{app_secret}"}
  r = requests.get(url, params=params, timeout=60)
  return r.json()

def exchange_long_lived_user_token(app_id: str, app_secret: str, short_lived_user_token: str) -> Dict[str, Any]:
  url = f"{GRAPH}/oauth/access_token"
  params = {
    "grant_type": "fb_exchange_token",
    "client_id": app_id,
    "client_secret": app_secret,
    "fb_exchange_token": short_lived_user_token
  }
  r = requests.get(url, params=params, timeout=60)
  return r.json()

def get_user_pages(long_lived_user_token: str) -> Dict[str, Any]:
  url = f"{GRAPH}/me/accounts"
  params = {"access_token": long_lived_user_token, "fields": "name,id,access_token,perms"}
  r = requests.get(url, params=params, timeout=120)
  return r.json()

def get_page_token(page_id: str, user_token: str) -> Dict[str, Any]:
  url = f"{GRAPH}/{page_id}"
  params = {"fields": "access_token,name,id", "access_token": user_token}
  r = requests.get(url, params=params, timeout=60)
  return r.json()

def post_text(page_id: str, page_access_token: str, message: str, link: Optional[str]=None, published: bool=True) -> Dict[str, Any]:
  url = f"{GRAPH}/{page_id}/feed"
  data = {"message": message, "published": str(published).lower(), "access_token": page_access_token}
  if link: data["link"] = link
  r = requests.post(url, data=data, timeout=180)
  try: return r.json()
  except Exception: return {"status_code": r.status_code, "text": r.text}

def post_video(page_id: str, page_access_token: str, video_path: Optional[str]=None, description: str="", fileobj=None) -> Dict[str, Any]:
  url = f"{GRAPH}/{page_id}/videos"
  params = {"access_token": page_access_token, "description": description}
  files = None
  if fileobj is not None:
    files = {"source": fileobj}
  elif video_path and os.path.isfile(video_path):
    files = {"source": open(video_path, "rb")}
  else:
    return {"error": {"message": "No video file provided"}}
  try:
    r = requests.post(url, params=params, files=files, timeout=600)
    return r.json()
  finally:
    if files and hasattr(files["source"], "close"):
      try: files["source"].close()
      except Exception: pass
