import logging, json, os, sys
from datetime import datetime
RESET='\x1b[0m'
try:
    from colorama import just_fix_windows_console
    just_fix_windows_console()
except Exception:
    pass
class JsonFormatter(logging.Formatter):
  def format(self, record):
    return json.dumps({'ts': datetime.utcnow().isoformat(timespec='milliseconds')+'Z','level': record.levelname,'name': record.name,'msg': record.getMessage()})
class ColorConsoleFormatter(logging.Formatter):
  def format(self, record):
    return f"[{datetime.utcnow().strftime('%H:%M:%S')}] {record.levelname:<8} {record.name}: {record.getMessage()}"

def build_logger(name: str, log_file: str, console_colors: bool = True, level: int = logging.INFO) -> logging.Logger:
  env_level = os.getenv("LOG_LEVEL", "").upper()
  if env_level in ("DEBUG","INFO","WARNING","ERROR","CRITICAL"):
    level = getattr(logging, env_level)
  lg=logging.getLogger(name); lg.setLevel(level); lg.propagate=False
  if not lg.handlers:
    ch=logging.StreamHandler(sys.stdout); ch.setLevel(level); ch.setFormatter(ColorConsoleFormatter()); lg.addHandler(ch)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    fh=logging.FileHandler(log_file, encoding='utf-8'); fh.setLevel(level); fh.setFormatter(JsonFormatter()); lg.addHandler(fh)
  return lg

def jsonl_write(path, obj):
  os.makedirs(os.path.dirname(path), exist_ok=True); open(path,'a',encoding='utf-8').write(json.dumps(obj)+'\n')
