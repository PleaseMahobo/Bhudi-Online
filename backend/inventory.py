import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

load_dotenv(dotenv_path=".env")

engine = create_engine(os.environ["DATABASE_URL"])
insp = inspect(engine)

for table in sorted(insp.get_table_names()):
    print("\n" + "=" * 80)
    print(table.upper())
    print("=" * 80)

    print("\nCOLUMNS")
    for col in insp.get_columns(table):
        print(col)

    print("\nPRIMARY KEY")
    print(insp.get_pk_constraint(table))

    print("\nFOREIGN KEYS")
    for fk in insp.get_foreign_keys(table):
        print(fk)

    print("\nINDEXES")
    for idx in insp.get_indexes(table):
        print(idx)

    print("\nUNIQUE")
    for uq in insp.get_unique_constraints(table):
        print(uq)