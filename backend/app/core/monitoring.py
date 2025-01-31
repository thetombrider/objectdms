import time
from typing import Callable
from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, CollectorRegistry, multiprocess, generate_latest
from .logging import app_logger

# Create a new registry
registry = CollectorRegistry()
multiprocess.MultiProcessCollector(registry)

# Define metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=registry
)

def setup_monitoring(app: FastAPI) -> None:
    """Setup monitoring middleware and endpoints."""
    
    @app.middleware("http")
    async def monitoring_middleware(request: Request, call_next: Callable) -> Response:
        """Middleware to collect metrics for each request."""
        # Start timer
        start_time = time.time()
        
        # Get path template if available (handles path parameters)
        path_template = request.url.path
        for route in request.app.routes:
            if route.path_regex.match(request.url.path):
                path_template = route.path
                break
        
        try:
            # Process request
            response = await call_next(request)
            
            # Record metrics
            http_requests_total.labels(
                method=request.method,
                endpoint=path_template,
                status=response.status_code
            ).inc()
            
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=path_template
            ).observe(time.time() - start_time)
            
            # Log request
            app_logger.info(
                f"{request.method} {path_template} {response.status_code} "
                f"[{time.time() - start_time:.3f}s]"
            )
            
            return response
            
        except Exception as e:
            # Record error metrics
            http_requests_total.labels(
                method=request.method,
                endpoint=path_template,
                status=500
            ).inc()
            
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=path_template
            ).observe(time.time() - start_time)
            
            # Log error
            app_logger.error(
                f"Error processing {request.method} {path_template}: {str(e)}"
            )
            raise
    
    @app.get("/metrics")
    async def metrics():
        """Endpoint to expose Prometheus metrics."""
        return Response(
            generate_latest(registry),
            media_type="text/plain"
        ) 