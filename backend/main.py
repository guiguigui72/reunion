import sys
import socket
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.setup import router as setup_router
from api.chat import router as chat_router
from api.settings import router as settings_router

app = FastAPI(title="重逢 Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(setup_router)
app.include_router(chat_router)
app.include_router(settings_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


def find_free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def main():
    port_file_path = sys.argv[1] if len(sys.argv) > 1 else None

    port = find_free_port()

    if port_file_path:
        pf = Path(port_file_path)
        pf.parent.mkdir(parents=True, exist_ok=True)
        pf.write_text(str(port))
        print(f"Port {port} written to {port_file_path}", flush=True)

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
