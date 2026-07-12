"""
validators.py

Validation framework for schema snapshots.

Validators never modify schemas. They only detect structural
problems before comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .types import SchemaInfo


# ==========================================================
# Validation Issue
# ==========================================================


@dataclass(slots=True)
class ValidationIssue:

    severity: str

    location: str

    message: str


# ==========================================================
# Validation Result
# ==========================================================


@dataclass(slots=True)
class ValidationResult:

    issues: list[ValidationIssue] = field(default_factory=list)

    def add(
        self,
        severity: str,
        location: str,
        message: str,
    ):

        self.issues.append(

            ValidationIssue(

                severity=severity,

                location=location,

                message=message,

            )

        )

    @property
    def valid(self):

        return not any(
            i.severity == "error"
            for i in self.issues
        )

    @property
    def warning_count(self):

        return sum(
            i.severity == "warning"
            for i in self.issues
        )

    @property
    def error_count(self):

        return sum(
            i.severity == "error"
            for i in self.issues
        )


# ==========================================================
# Validator
# ==========================================================


class SchemaValidator:

    def validate(
        self,
        schema: SchemaInfo,
    ) -> ValidationResult:

        result = ValidationResult()

        if not schema.tables:

            result.add(

                "error",

                "schema",

                "No tables found."

            )

            return result

        #
        # Validate every table
        #

        for table in schema.tables.values():

            if not table.name:

                result.add(

                    "error",

                    "table",

                    "Unnamed table."

                )

            if not table.columns:

                result.add(

                    "warning",

                    table.name,

                    "Table contains no columns."

                )

            #
            # Validate columns
            #

            for column in table.columns.values():

                if not column.name:

                    result.add(

                        "error",

                        table.name,

                        "Unnamed column."

                    )

                if not column.data_type:

                    result.add(

                        "warning",

                        f"{table.name}.{column.name}",

                        "Missing datatype."

                    )

            #
            # Primary key
            #

            if table.primary_key is None:

                result.add(

                    "warning",

                    table.name,

                    "Table has no primary key."

                )

        return result


# ==========================================================
# Convenience
# ==========================================================


def validate_schema(
    schema: SchemaInfo,
) -> ValidationResult:

    return SchemaValidator().validate(schema)