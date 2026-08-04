from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session


@dataclass
class SecretEntry:
    name: str
    value: str
    category: str | None = None


class SecretsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _key(self) -> bytes:
        return os.getenv("BHUDI_ENCRYPTION_KEY", "local-dev-key").encode("utf-8")

    def _protect(self, value: str) -> str:
        key = self._key()
        encoded = bytearray(value.encode("utf-8"))
        for index, byte in enumerate(encoded):
            encoded[index] = byte ^ key[index % len(key)]
        return base64.b64encode(bytes(encoded)).decode("utf-8")

    def _unprotect(self, value: str) -> str:
        key = self._key()
        decoded = bytearray(base64.b64decode(value.encode("utf-8")))
        for index, byte in enumerate(decoded):
            decoded[index] = byte ^ key[index % len(key)]
        return bytes(decoded).decode("utf-8")

    def store_secret(self, name: str, value: str, *, category: str | None = None) -> SecretEntry:
        from app.models.secret_entry import SecretEntry as SecretEntryModel

        payload = self._protect(value)
        entry = self.db.query(SecretEntryModel).filter(SecretEntryModel.name == name).first()
        if entry is None:
            entry = SecretEntryModel(name=name, value=payload, category=category)
            self.db.add(entry)
        else:
            entry.value = payload
            entry.category = category
        self.db.flush()
        return SecretEntry(name=entry.name, value=self._unprotect(entry.value), category=entry.category)

    def get_secret(self, name: str) -> str | None:
        from app.models.secret_entry import SecretEntry as SecretEntryModel

        entry = self.db.query(SecretEntryModel).filter(SecretEntryModel.name == name).first()
        if entry is None:
            return None
        return self._unprotect(entry.value)

    def get_secret_value(self, name: str) -> str | None:
        from app.models.secret_entry import SecretEntry as SecretEntryModel

        entry = self.db.query(SecretEntryModel).filter(SecretEntryModel.name == name).first()
        if entry is None:
            return None
        return self._unprotect(entry.value)

    def get_backend_name(self) -> str:
        return "xor"

    def get_key_length(self) -> int:
        key = self._key()
        return max(16, len(key))
