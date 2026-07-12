from tools.schema_sync import SchemaSynchronizer


class SchemaService:

    def __init__(self):
        self.synchronizer = SchemaSynchronizer()

    def get_status(self):
        # Temporary schemas until we connect the real DB introspection
        source_schema = {
            "devices": {
                "id": "uuid",
                "hostname": "string"
            },
            "users": {
                "id": "uuid"
            }
        }

        target_schema = {
            "devices": {
                "id": "uuid",
                "hostname": "string"
            },
            "users": {
                "id": "uuid"
            }
        }

        result = self.synchronizer.analyze(
            source_schema,
            target_schema
        )

        return {
            "health_score": result.drift.health_score,
            "drift_score": result.drift.drift_score,
            "identical": result.drift.identical,
            "differences": result.comparison.differences,
        }