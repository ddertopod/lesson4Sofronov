from __future__ import annotations
import time, io
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import requests
from .config import AppConfig
from .logger import build_logger, jsonl_write
@dataclass
class MetricSnapshot:
  ts:str; response_times_ms:List[float]; p95_latency_ms:float; error_rate_percent:float; health_ok:bool; consecutive_failures:int
class ServiceMonitor:
  def __init__(self,cfg:AppConfig):
    self.cfg=cfg; self.base_url=cfg.service.base_url.rstrip('/'); self.timeout=cfg.monitoring.request_timeout_seconds; self.samples=cfg.monitoring.samples_per_check; self.logger=build_logger('monitor', cfg.logging.log_file, cfg.logging.console_colors); self.metrics_file=cfg.logging.metrics_file; self.consecutive_failures=0
    self.inf = cfg.inference
    self.batch_size = int(self.inf.files_per_request)
    self.batch_ep  = getattr(cfg, "endpoints", {}).get("batch", "/predict_batch")
    self.logger.info(
        f"Monitor started: base_url={self.base_url}, timeout={self.timeout}s, "
        f"samples={self.samples}, metrics_file={self.metrics_file}"
    )
    if hasattr(self, "batch_size"):
        self.logger.info(f"Inference mode={getattr(self, 'inf', None) and self.inf.mode}, batch_size={self.batch_size}")
    try:
        import csv, os
        csv_path = (self.inf.load_batch_from_csv or '').strip()
        if csv_path and os.path.exists(csv_path):
            best_key=None; best_bs=None
            with open(csv_path, 'r', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    try:
                        bs = int(float(row.get('batch_size', 1)))
                        thr = float(row.get('throughput_samples_per_sec', 0.0))
                        p95t= float(row.get('p95_latency_total_ms', 1e18))
                    except Exception:
                        continue
                    key=(thr, -p95t)
                    if best_key is None or key>best_key:
                        best_key=key; best_bs=bs
            if best_bs:
                self.batch_size=max(1,best_bs)
        else:
            self.batch_size=max(1,int(self.inf.batch_size_fallback))
    except Exception:
        self.batch_size=max(1,int(self.inf.batch_size_fallback))
  def _health(self):
    try:
      t0=time.perf_counter(); r=requests.get(f"{self.base_url}/health", timeout=self.timeout); dt=(time.perf_counter()-t0)*1000; ok=r.status_code==200; return ok, {'rt_ms':dt,'status_code':r.status_code}
    except Exception as e:
      return False, {'error': str(e)}
    
  def _gen_image(self, fmt="JPEG"):
    import io
    buf = io.BytesIO()
    try:
        from PIL import Image
        import numpy as np
        arr = (np.random.rand(64, 64, 3) * 255).astype("uint8")
        Image.fromarray(arr).save(buf, format=fmt)
    except Exception:
        
        buf.write(b"\xff\xd8\xff")  
    buf.seek(0)
    return buf

  def _make_file_objects(self, n: int):
    import os, glob, random
    field = getattr(self.inf, 'multipart_field_name', 'files') or 'files'
    items = []

    src = (getattr(self.inf, 'file_source_dir', '') or '').strip()
    paths = []
    if src:
        if os.path.isdir(src):
            paths = sorted(
                glob.glob(os.path.join(src, "*.jpg")) +
                glob.glob(os.path.join(src, "*.jpeg")) +
                glob.glob(os.path.join(src, "*.png"))
            )
            if len(paths) >= n:
                chosen = random.sample(paths, n)
            else:
                chosen = [random.choice(paths)] * n if paths else []
        elif os.path.isfile(src):
            chosen = [src] * n
        else:
            chosen = []
    else:
        chosen = []

    if not chosen:
        for i in range(n):
            items.append((field, (f"sample_{i}.jpg", self._gen_image("JPEG"), "image/jpeg")))
        return items
    
    for p in chosen:
        ext = os.path.splitext(p)[1].lower()
        mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
        items.append((field, (os.path.basename(p), open(p, "rb"), mime)))
    return items

  def _predict_once(self):
    url=f"{self.base_url}/predict_batch"; t0=time.perf_counter()
    mode = getattr(self.inf, 'mode', 'multi-file')
    data = {}
    if mode == 'multi-file':
      files = self._make_file_objects(self.batch_size)
    elif mode == 'param':
      files = self._make_file_objects(1)
      data[getattr(self.inf, 'batch_param_name', 'batch_size')] = str(self.batch_size)
    else:
      files = self._make_file_objects(1)
    try:
      r=requests.post(url, files=files, data=data, timeout=self.timeout); dt=(time.perf_counter()-t0)*1000; ok=r.status_code==200; return ok, dt, {'status_code': r.status_code, 'batch_size': self.batch_size}
    except Exception as e:
      dt=(time.perf_counter()-t0)*1000; return False, dt, {'error': str(e)}
  def _p95(self, xs:List[float])->float:
    if not xs: return 0.0
    ys=sorted(xs); import math
    k=max(0, math.ceil(0.95*len(ys))-1); return float(ys[k])
  def run_check_once(self)->MetricSnapshot:
    self.logger.debug("Начат новый цикл проверок")
    import statistics, datetime
    health_ok, _ = self._health()
    rts=[]; ok_flags=[]
    for _ in range(self.samples):
      ok, rt, _ = self._predict_once(); rts.append(rt); ok_flags.append(ok)
    errors=sum(1 for s in ok_flags if not s); total=max(1,len(ok_flags)); err=errors*100.0/total
    snap=MetricSnapshot(datetime.datetime.utcnow().isoformat(timespec='seconds')+'Z', rts, self._p95(rts), err, health_ok, self.consecutive_failures)
    jsonl_write(self.metrics_file, {'ts': snap.ts,'response_times_ms': rts,'p95_latency_ms': snap.p95_latency_ms,'error_rate_percent': snap.error_rate_percent,'health_ok': snap.health_ok,'consecutive_failures': snap.consecutive_failures,'batch_size': self.batch_size})
    return snap