"""Main entry point for sample processor service."""
import os
import sys

# Add the parent directory to the Python path to ensure imports work correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check if we should run the demo or the API
if os.getenv("RUN_DEMO", "false").lower() == "true":
    import asyncio

    from sample_processor.main import main

    asyncio.run(main())
else:
    # Run the API server
    import uvicorn

    uvicorn.run(
        "sample_processor.api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8099")),
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        reload=False,
    )
