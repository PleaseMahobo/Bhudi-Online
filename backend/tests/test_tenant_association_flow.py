from types import SimpleNamespace
from uuid import uuid4

from app.api.v1.endpoints.tenant_context import set_tenant_context, TenantContextRequest


def test_tenant_context_binds_existing_tenant():
    tenant_id = uuid4()
    tenant = SimpleNamespace(id=tenant_id, name="Customer One")
    user = SimpleNamespace(id=uuid4(), tenant_id=None)

    class DB:
        def get(self, model, key):
            assert key == tenant_id
            return tenant
        def add(self, value):
            assert value is user
        def commit(self):
            pass
        def refresh(self, value):
            pass

    result = set_tenant_context(TenantContextRequest(tenant_id=tenant_id), user, DB())

    assert user.tenant_id == tenant_id
    assert result["tenant_id"] == str(tenant_id)
    assert result["tenant_name"] == "Customer One"
