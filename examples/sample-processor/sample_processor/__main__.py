"""Main entry point for sample processor service."""
import os

# Check if we should run the demo or the API
if os.getenv("RUN_DEMO", "false").lower() == "true":
    import asyncio

    from .main import main

    asyncio.run(main())
else:
    # Run the API server
    import uvicorn

    uvicorn.run(
        "sample_processor.api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8099")),
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
