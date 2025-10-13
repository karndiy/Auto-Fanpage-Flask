from flask import Flask, jsonify, request, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import os, json, logging
from logging.handlers import RotatingFileHandler
from utils.facebook import (
  load_settings, save_settings, exchange_long_lived_user_token,
  get_user_pages, get_page_token, post_text, post_video, debug_token
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
LOG_FILE = os.path.join(APP_DIR, "logs", "app.log")

app = Flask(__name__)

# Ensure the logs directory exists before creating the handler
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
formatter = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

scheduler = BackgroundScheduler(timezone="Asia/Bangkok")
scheduler_started = False

def start_scheduler():
  global scheduler_started
  if not scheduler_started:
    scheduler.start()
    scheduler_started = True

def clear_jobs():
  for j in scheduler.get_jobs():
    scheduler.remove_job(j.id)

def reload_jobs():
  s = load_settings(SETTINGS_FILE)
  clear_jobs()
  jobs = s.get("scheduler", {}).get("jobs", [])
  for idx, job in enumerate(jobs):
    jtype = job.get("type")
    cron = job.get("run_cron", "0 9 * * *")
    trig = CronTrigger.from_crontab(cron, timezone=s.get("scheduler", {}).get("timezone", "Asia/Bangkok"))
    if jtype == "text":
      msg = job.get("message", s.get("default_message", "Hello!"))
      link = job.get("link", s.get("post_defaults", {}).get("link"))
      published = job.get("published", s.get("post_defaults", {}).get("published", True))
      scheduler.add_job(lambda m=msg,l=link,p=published: do_post_text(m,l,p), trig, id=f"text_{idx}")
    elif jtype == "video":
      vpath = job.get("video_path")
      desc = job.get("description", "")
      scheduler.add_job(lambda vp=vpath,d=desc: do_post_video(vp,d), trig, id=f"video_{idx}")
  return {"jobs": [j.id for j in scheduler.get_jobs()]}

def do_post_text(message, link, published):
  s = load_settings(SETTINGS_FILE)
  page_id = s.get("page_id")
  pat = s.get("page_access_token")
  if not page_id or not pat: return
  res = post_text(page_id, pat, message, link, published)
  app.logger.info(f"Post text result: {res}")

def do_post_video(video_path, description):
  s = load_settings(SETTINGS_FILE)
  page_id = s.get("page_id")
  pat = s.get("page_access_token")
  if not page_id or not pat: return
  res = post_video(page_id, pat, video_path=video_path, description=description)
  app.logger.info(f"Post video result: {res}")

@app.route("/")
def index():
  return render_template("index.html")

@app.route("/help")
def help_page():
  return render_template("help.html")

@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
  if request.method == "GET":
    return jsonify(load_settings(SETTINGS_FILE))
  data = request.get_json(force=True, silent=True) or {}
  current = load_settings(SETTINGS_FILE)
  current.update({
    "app_id": data.get("app_id", current.get("app_id")),
    "app_secret": data.get("app_secret", current.get("app_secret")),
    "short_lived_user_token": data.get("short_lived_user_token", current.get("short_lived_user_token")),
    "long_lived_user_token": data.get("long_lived_user_token", current.get("long_lived_user_token")),
    "page_id": data.get("page_id", current.get("page_id")),
    "page_access_token": data.get("page_access_token", current.get("page_access_token")),
    "default_message": data.get("default_message", current.get("default_message")),
    "post_defaults": data.get("post_defaults", current.get("post_defaults")),
  })
  save_settings(current, SETTINGS_FILE)
  return jsonify({"ok": True, "settings": current})

@app.route("/api/exchange_user_token", methods=["POST"])
def api_exchange():
  s = load_settings(SETTINGS_FILE)
  res = exchange_long_lived_user_token(s.get("app_id",""), s.get("app_secret",""), s.get("short_lived_user_token",""))
  if "access_token" in res:
    s["long_lived_user_token"] = res["access_token"]
    save_settings(s, SETTINGS_FILE)
  return jsonify(res)

@app.route("/api/pages", methods=["GET"])
def api_pages():
  s = load_settings(SETTINGS_FILE)
  res = get_user_pages(s.get("long_lived_user_token",""))
  return jsonify(res)

@app.route("/api/page_token", methods=["POST"])
def api_page_token():
  s = load_settings(SETTINGS_FILE)
  page_id = s.get("page_id","")
  user_token = s.get("long_lived_user_token","")
  res = get_page_token(page_id, user_token)
  token = res.get("access_token")
  if token:
    s["page_access_token"] = token
    save_settings(s, SETTINGS_FILE)
  return jsonify(res)

@app.route("/api/post_text", methods=["POST"])
def api_post_text():
  s = load_settings(SETTINGS_FILE)
  data = request.get_json(force=True, silent=True) or {}
  message = data.get("message") or s.get("default_message", "Hello!")
  link = data.get("link") or s.get("post_defaults", {}).get("link")
  published = data.get("published")
  if published is None:
    published = s.get("post_defaults", {}).get("published", True)
  res = post_text(s.get("page_id",""), s.get("page_access_token",""), message, link, bool(published))
  return jsonify(res)

@app.route("/api/post_video", methods=["POST"])
def api_post_video():
  s = load_settings(SETTINGS_FILE)
  description = request.form.get("description","")
  video_path = request.form.get("video_path")
  file = request.files.get("file")
  fileobj = None
  if file:
    fileobj = (file.filename, file.stream, file.mimetype or "video/mp4")
  res = post_video(s.get("page_id",""), s.get("page_access_token",""), video_path=video_path, description=description, fileobj=fileobj)
  return jsonify(res)

@app.route("/api/scheduler/toggle", methods=["POST"])
def api_sched_toggle():
  payload = request.get_json(force=True, silent=True) or {}
  enabled = bool(payload.get("enabled", False))
  s = load_settings(SETTINGS_FILE)
  s.setdefault("scheduler",{})
  s["scheduler"]["enabled"] = enabled
  save_settings(s, SETTINGS_FILE)
  if enabled:
    start_scheduler()
    jobs = reload_jobs()
    return jsonify({"ok": True, "enabled": True, "jobs": jobs})
  else:
    clear_jobs()
    return jsonify({"ok": True, "enabled": False})

@app.route("/api/scheduler/reload", methods=["POST"])
def api_sched_reload():
  s = load_settings(SETTINGS_FILE)
  if not s.get("scheduler",{}).get("enabled", False):
    return jsonify({"ok": False, "error": "Scheduler is disabled"}), 400
  start_scheduler()
  jobs = reload_jobs()
  return jsonify({"ok": True, "jobs": jobs})

if __name__ == "__main__":
  s = load_settings(SETTINGS_FILE)
  if s.get("scheduler",{}).get("enabled", False):
    start_scheduler()
    reload_jobs()
  app.run(host="0.0.0.0", port=5000, debug=True)
