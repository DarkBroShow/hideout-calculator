from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str
    maintenance: bool = False
    db_commit: str | None = None