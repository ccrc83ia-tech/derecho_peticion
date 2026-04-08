class DomainException(Exception):
    def __init__(self, message: str, code: str) -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class TenantNotFoundException(DomainException):
    def __init__(self, tenant_id: str) -> None:
        super().__init__(f"Tenant '{tenant_id}' not found", "TENANT_NOT_FOUND")


class DocumentGenerationException(DomainException):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Document generation failed: {reason}", "GENERATION_FAILED")


class InvalidSchemaException(DomainException):
    def __init__(self, missing: list[str]) -> None:
        super().__init__(f"Missing required fields: {', '.join(missing)}", "INVALID_SCHEMA")


class AuthenticationException(DomainException):
    def __init__(self, reason: str = "Credenciales inválidas") -> None:
        super().__init__(reason, "AUTH_FAILED")


class AuthorizationException(DomainException):
    def __init__(self, permission: str = "") -> None:
        msg = f"Sin permiso: {permission}" if permission else "Acceso denegado"
        super().__init__(msg, "FORBIDDEN")
