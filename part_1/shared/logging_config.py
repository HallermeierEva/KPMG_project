"""
Centralized logging configuration for all microservices
"""
import logging
import sys
from datetime import datetime, timezone
import json


class StructuredLogger:
    """JSON structured logger for microservices"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers
        self.logger.handlers = []

        # Console handler with JSON formatting
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.JsonFormatter(service_name))
        self.logger.addHandler(handler)

    class JsonFormatter(logging.Formatter):
        def __init__(self, service_name):
            self.service_name = service_name
            super().__init__()

        def format(self, record):
            log_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),  # Fixed deprecation
                "service": self.service_name,
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
            }

            # Add extra fields if present
            if hasattr(record, 'extra_data'):
                log_data.update(record.extra_data)

            # Add exception info if present
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)

            return json.dumps(log_data, ensure_ascii=False)

    def info(self, message: str, **kwargs):
        """Log info with structured phase2_data"""
        extra = {'extra_data': kwargs}
        self.logger.info(message, extra=extra)

    def error(self, message: str, **kwargs):
        """Log error with structured phase2_data"""
        extra = {'extra_data': kwargs}
        self.logger.error(message, extra=extra)

    def warning(self, message: str, **kwargs):
        """Log warning with structured phase2_data"""
        extra = {'extra_data': kwargs}
        self.logger.warning(message, extra=extra)


# Factory function
def get_logger(service_name: str) -> StructuredLogger:
    """Get structured logger for a service"""
    return StructuredLogger(service_name)