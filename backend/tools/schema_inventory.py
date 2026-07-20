from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

load_dotenv()

engine = create_engine(os.environ["DATABASE_URL"])
inspector = inspect(engine)

inventory = {}

for table in sorted(inspector.get_table_names()):
    inventory[table] = {
        "columns": inspector.get_columns(table),
        "primary_key": inspector.get_pk_constraint(table),
        "foreign_keys": inspector.get_foreign_keys(table),
        "indexes": inspector.get_indexes(table),
        "unique_constraints": inspector.get_unique_constraints(table),
        "check_constraints": inspector.get_check_constraints(table),
    }

with open("schema_inventory.json", "w", encoding="utf-8") as f:
    json.dump(inventory, f, indent=2, default=str)

print(f"Inventory created for {len(inventory)} tables.")