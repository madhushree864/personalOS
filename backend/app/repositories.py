from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import AuditEntry, Document, HealthRecord, Holding, InvestmentApproval, InvestmentProposal, Renewal, User

class Repository:
    def __init__(self, db: Session, owner_id: str | None = None):
        self.db, self.owner_id = db, owner_id
    def user(self, email): return self.db.scalar(select(User).where(User.email == email))
    def _owned(self, model):
        q = select(model)
        if self.owner_id:
            # NULL ownership is legacy data only and must not be exposed to a
            # different authenticated principal.
            q = q.where(model.owner_id == self.owner_id)
        else:
            q = q.where(model.owner_id.is_(None))
        return q
    def renewals(self): return list(self.db.scalars(self._owned(Renewal).order_by(Renewal.due_date)))
    def health(self): return list(self.db.scalars(self._owned(HealthRecord).order_by(HealthRecord.date)))
    def holdings(self): return list(self.db.scalars(self._owned(Holding).order_by(Holding.symbol)))
    def audit(self, limit=10):
        query = select(AuditEntry)
        if self.owner_id:
            query = query.where(AuditEntry.user_id == self.owner_id)
        else:
            query = query.where(AuditEntry.user_id.is_(None))
        return list(self.db.scalars(query.order_by(AuditEntry.timestamp.desc()).limit(limit)))
    def proposal(self, proposal_id): return self.db.scalar(self._owned(InvestmentProposal).where(InvestmentProposal.id == proposal_id))
    def approval(self, proposal_id):
        return self.db.scalar(select(InvestmentApproval).where(
            InvestmentApproval.proposal_id == proposal_id, InvestmentApproval.owner_id == self.owner_id))
    def proposals(self, limit=20): return list(self.db.scalars(self._owned(InvestmentProposal).order_by(InvestmentProposal.id.desc()).limit(limit)))
    def log(self, event, details=None, user_id=None):
        entry = AuditEntry(event=event, details=details or {}, user_id=user_id or self.owner_id)
        self.db.add(entry); self.db.commit(); self.db.refresh(entry); return entry
    def create_document(self, **values):
        document = Document(owner_id=self.owner_id, **values)
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document
    def document(self, document_id):
        return self.db.scalar(self._owned(Document).where(Document.id == document_id))
    def documents(self, limit=100):
        return list(self.db.scalars(
            self._owned(Document).order_by(Document.created_at.desc()).limit(limit)
        ))
