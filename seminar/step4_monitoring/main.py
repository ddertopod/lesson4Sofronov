import argparse
import time
from src.config import load_config
from src.monitor import ServiceMonitor

p=argparse.ArgumentParser(); p.add_argument('-c','--config', default='config/monitoring_config.yaml'); p.add_argument('--once', action='store_true'); args=p.parse_args()
cfg=load_config(args.config); mon=ServiceMonitor(cfg)
if args.once: mon.run_check_once()
else:
  while True:
    mon.run_check_once(); time.sleep(cfg.monitoring.check_interval_seconds)

