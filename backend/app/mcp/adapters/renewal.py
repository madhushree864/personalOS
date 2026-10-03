from ...services import serialize_renewal
from ...repositories import Repository
from ..contracts import RenewalReadResponse


class RenewalMCPAdapter:
    """Reads renewals through an already owner-bound repository."""

    def __init__(self, repository: Repository):
        if not repository.owner_id:
            raise ValueError("an authenticated repository owner is required")
        self.repository = repository

    def read(self, query: str, context) -> dict:
        if context.user_id != self.repository.owner_id:
            raise ValueError("MCP context does not match the repository owner")
        response = RenewalReadResponse(
            query=query,
            renewals=[serialize_renewal(item) for item in self.repository.renewals()],
        )
        return response.model_dump(mode="json")
