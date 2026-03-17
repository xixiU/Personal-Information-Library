#!/usr/bin/env python
"""启动脚本 - 可以直接通过 python run.py 运行."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
