from pydantic import BaseModel

class BatchJobStatus(BaseModel):
    batch_id: str
    status: str
    # Add other relevant fields like created_at, completed_at, etc. if needed 