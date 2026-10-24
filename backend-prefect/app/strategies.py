from abc import ABC, abstractmethod
from .errors import AuthError
from .totp import match_window


class SecondFactorStrategy(ABC):
    @abstractmethod
    def validate(self, store, user_id, code, now) -> int | None:
        """Valida sin consumir: el consumo ocurre en la transacción final."""


class TOTPStrategy(SecondFactorStrategy):
    def validate(self, store, user_id, code, now):
        factor = store.factor(user_id)
        if not factor or factor["state"] != "ACTIVE":
            raise AuthError("Activa 2FA antes de ingresar")
        window = match_window(factor["secret"], code, now)
        if window is None:
            raise AuthError("Código TOTP inválido o expirado")
        return window


class BackupCodeStrategy(SecondFactorStrategy):
    def validate(self, store, user_id, code, now):
        factor = store.factor(user_id)
        if not factor or factor["state"] != "ACTIVE" or not store.has_backup(user_id, code):
            raise AuthError("Código de respaldo inválido o utilizado")
        return None
