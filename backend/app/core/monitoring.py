"""Monitoring setup for the application."""

import os
from typing import Optional
from fastapi import FastAPI
from prometheus_client import (
    Counter, Histogram, multiprocess, CollectorRegistry, CONTENT_TYPE_LATEST,
    generate_latest
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.requests import Request
from starlette.routing import Match
from time import time
from .logging import app_logger

# Initialize metrics registry
registry = CollectorRegistry()
if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
    multiprocess.MultiProcessCollector(registry)

# Define metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total count of HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=registry
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=registry
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and collect metrics."""
        method = request.method
        path_template = self._get_path_template(request)
        
        start_time = time()
        response = await call_next(request)
        duration = time() - start_time
        
        status_code = str(response.status_code)
        
        http_requests_total.labels(
            method=method,
            endpoint=path_template,
            status_code=status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=path_template
        ).observe(duration)
        
        return response
    
    @staticmethod
    def _get_path_template(request: Request) -> str:
        """Get the path template for a request."""
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return route.path
        return request.url.path

async def metrics(request: Request) -> Response:
    """Endpoint to expose Prometheus metrics."""
    return Response(
        generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST
    )

def setup_monitoring(app: FastAPI) -> None:
    """Set up monitoring for the application."""
    # Add Prometheus middleware
    app.add_middleware(PrometheusMiddleware)
    
    # Add metrics endpoint
    app.add_route("/metrics", metrics)

    @app.middleware("http")
    async def monitoring_middleware(request: Request, call_next):
        """Middleware to collect metrics for each request."""
        # Start timer
        start_time = time()
        
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
                status_code=str(response.status_code)
            ).inc()
            
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=path_template
            ).observe(time() - start_time)
            
            # Log request
            app_logger.info(
                f"{request.method} {path_template} {response.status_code} "
                f"[{time() - start_time:.3f}s]"
            )
            
            return response
            
        except Exception as e:
            # Record error metrics
            http_requests_total.labels(
                method=request.method,
                endpoint=path_template,
                status_code="500"
            ).inc()
            
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=path_template
            ).observe(time() - start_time)
            
            # Log error
            app_logger.error(
                f"Error processing {request.method} {path_template}: {str(e)}"
            )
            raise 