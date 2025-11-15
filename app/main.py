from fastapi import FastAPI

app = FastAPI(title="TCF Learning Service")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Basic health endpoint for initial skeleton."""
    return {"status": "ok"}
