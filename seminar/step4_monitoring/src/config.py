import os
from dataclasses import dataclass
from typing import Any, Dict, Optional
import yaml

DEFAULT_CONFIG_PATH = os.environ.get("MONITORING_CONFIG", "seminar/step4_monitoring/config/monitoring_config.yaml")

@dataclass
class ServiceConfig:
    host: str = "localhost"
    port: int = 8000
    base_url: str = "http://localhost:8000"

@dataclass
class MonitoringConfig:
    check_interval_seconds: int = 30
    samples_per_check: int = 3
    request_timeout_seconds: int = 10

@dataclass
class Thresholds:
    response_time_ms: Dict[str, float]
    p95_latency_ms: Dict[str, float]
    error_rate_percent: Dict[str, float]
    consecutive_failures: Dict[str, int]

@dataclass
class AlertsConfig:
    enabled: bool = True
    cooldown_minutes: int = 5

@dataclass
class LoggingConfig:
    console_colors: bool = True
    log_file: str = "logs/monitoring.log"
    metrics_file: str = "logs/metrics.jsonl"

@dataclass
class InferenceConfig:
    load_batch_from_csv: str = "results/optimization_results.csv"
    batch_size_fallback: int = 1
    mode: str = "multi-file"  
    multipart_field_name: str = "files"
    batch_param_name: str = "batch_size"
    files_per_request: int = 1
    file_source_dir: str = ""

@dataclass
class AppConfig:
    service: ServiceConfig
    monitoring: MonitoringConfig
    thresholds: Thresholds
    alerts: AlertsConfig
    logging: LoggingConfig
    inference: InferenceConfig

def load_config(path: Optional[str] = None) -> AppConfig:
    path = DEFAULT_CONFIG_PATH
    raw=yaml.safe_load(open(path,'r',encoding='utf-8'))
    service = ServiceConfig(**raw.get("service", {}))
    monitoring = MonitoringConfig(**raw.get("monitoring", {}))
    thresholds = Thresholds(**raw.get("thresholds", {}))
    alerts = AlertsConfig(**raw.get("alerts", {}))
    logging = LoggingConfig(**raw.get("logging", {}))
    inference = InferenceConfig(**raw.get("inference", {}))
    return AppConfig(service=service, monitoring=monitoring, thresholds=thresholds, alerts=alerts, logging=logging, inference=inference)
