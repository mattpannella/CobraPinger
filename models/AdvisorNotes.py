from pydantic import BaseModel

class AdvisorNote(BaseModel):
    key: str
    content: str

class AdvisorNotes(BaseModel):
    notes: list[AdvisorNote]