from tools.schema_sync import (
    SchemaSynchronizer,
    SchemaInspector,
)

from app.core.database import engine

class SchemaService:

    def __init__(self):
        self.synchronizer = SchemaSynchronizer()
        self.inspector = SchemaInspector(engine)

    def get_status(self):
        # Temporary schemas until we connect the real DB introspection
        current_schema = self.inspector.inspect()

        source_schema = current_schema
        target_schema = current_schema

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