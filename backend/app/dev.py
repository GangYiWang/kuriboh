"""Development server entry point with Windows-friendly console output."""

import os

import uvicorn


def main() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        use_colors=False,
    )


if __name__ == "__main__":
    main()
