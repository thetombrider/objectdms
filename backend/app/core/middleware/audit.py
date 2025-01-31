from typing import Callable
from fastapi import FastAPI, Request, Response
from ...models.audit import AuditLog
from ..logging import app_logger

def setup_audit_middleware(app: FastAPI) -> None:
    """Setup audit logging middleware."""
    
    @app.middleware("http")
    async def audit_middleware(request: Request, call_next: Callable) -> Response:
        """Middleware to log API requests to audit log."""
        # Get path template if available (handles path parameters)
        path_template = request.url.path
        for route in request.app.routes:
            if route.path_regex.match(request.url.path):
                path_template = route.path
                break
        
        # Extract resource type and action from path
        parts = path_template.split("/")
        if len(parts) > 3:  # /api/v1/{resource}/{action}
            resource_type = parts[3]  # e.g., "documents", "users"
            action = request.method.lower()
            
            try:
                # Process request
                response = await call_next(request)
                
                # Log successful request
                if hasattr(request.state, "user_id"):
                    await AuditLog.log_event(
                        user=request.state.user_id,
                        action=action,
                        resource_type=resource_type,
                        resource_id=parts[4] if len(parts) > 4 else "",
                        details={
                            "method": request.method,
                            "path": path_template,
                            "status_code": response.status_code
                        },
                        ip_address=request.client.host,
                        user_agent=request.headers.get("user-agent"),
                        status="success" if response.status_code < 400 else "failure"
                    )
                
                return response
                
            except Exception as e:
                # Log failed request
                if hasattr(request.state, "user_id"):
                    await AuditLog.log_event(
                        user=request.state.user_id,
                        action=action,
                        resource_type=resource_type,
                        resource_id=parts[4] if len(parts) > 4 else "",
                        details={
                            "method": request.method,
                            "path": path_template,
                            "error": str(e)
                        },
                        ip_address=request.client.host,
                        user_agent=request.headers.get("user-agent"),
                        status="failure",
                        error_message=str(e)
                    )
                
                app_logger.error(f"Error in request: {str(e)}")
                raise
        
        # If path doesn't match pattern, just process request
        return await call_next(request) 