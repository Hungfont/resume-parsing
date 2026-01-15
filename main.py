"""Main entry point for running the FastAPI application with auto-reload."""
import uvicorn

from be.api import app
from be.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.app_name} v{settings.version}")
    print(f"Debug mode: {settings.debug}")
    print(f"Database: {settings.db.url.split('@')[-1] if '@' in settings.db.url else 'SQLite'}")
    print(f"Auto-reload: {'Enabled' if settings.debug else 'Disabled'}")
    print("-" * 50)
    
    uvicorn.run(
        "be.api:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        reload_dirs=["be", "ai", "config"] if settings.debug else None,
        reload_includes=["*.py", "*.json"] if settings.debug else None,
        log_level=settings.logging.level.lower(),
    )
