from sqlalchemy.orm import Session

from ..models import Document
from ..repositories import Repository


class DocumentRepository:
    def __init__(self, db: Session, owner_id: str):
        self.repository = Repository(db, owner_id)

    @property
    def owner_id(self) -> str:
        return self.repository.owner_id

    def create(self, **values) -> Document:
        return self.repository.create_document(**values)

    def get_owned(self, document_id: str) -> Document | None:
        return self.repository.document(document_id)

    def list_owned(self, limit: int = 100) -> list[Document]:
        return self.repository.documents(limit)
