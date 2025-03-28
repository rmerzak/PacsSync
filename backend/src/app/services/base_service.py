class BaseService:
    def __init__(self, repository):
        self.repository = repository

    # Common utility for all services, for example, logging or error handling
    def validate_required_fields(self, data: dict, required_fields: list):
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValueError(f"Missing required field: {field}")
    async def close_scoped_session(self):
        await self.repository.close_scoped_session()