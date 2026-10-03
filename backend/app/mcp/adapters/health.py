from ...repositories import Repository
from ...services import serialize_health
from ..contracts import HealthReadResponse


class HealthMCPAdapter:
    """Reads health records through an already owner-bound repository."""

    def __init__(self, repository: Repository):
        if not repository.owner_id:
            raise ValueError("an authenticated repository owner is required")
        self.repository = repository

    def read(self, metric: str, context) -> dict:
        if context.user_id != self.repository.owner_id:
            raise ValueError("MCP context does not match the repository owner")
        records = [
            serialize_health(item)
            for item in self.repository.health()
            if not metric or item.metric == metric
        ]
        return HealthReadResponse(metric=metric, records=records).model_dump(mode="json")
