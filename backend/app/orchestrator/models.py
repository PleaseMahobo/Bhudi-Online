from fastapi import FastAPI
from app.orchestrator.engine import OrchestratorEngine
from app.orchestrator.rules_engine import RulesEngine
from app.orchestrator.incident_builder import IncidentBuilder

app = FastAPI()

engine = OrchestratorEngine()
rules = RulesEngine()
builder = IncidentBuilder()

@app.post("/event")
def receive_event(event: dict):

    engine.ingest(event)

    # rule evaluation
    incident = rules.evaluate(event)

    if incident:
        return {"status": "incident_created", "incident": incident}

    grouped = builder.add_event(event)

    if grouped:
        return {"status": "group_incident", "incident": grouped}

    return {"status": "ok"}