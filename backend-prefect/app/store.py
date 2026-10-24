import hashlib
import hmac
from pathlib import Path
import sqlite3
import threading
from cryptography.fernet import Fernet
from .errors import AuthError, ReplayAttackDetected, TooManyAttempts


class Store:
    """PoC de un proceso: lock cubre check, estrategia y commit, incluso entre hilos.

    SQLite persiste replay entre reinicios. Para varios workers se requiere un
    bloqueo transaccional compartido en Postgres/Redis (ver docs/arquitectura.md).
    """
    def __init__(self, path: str, key: str, digest_key: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.fernet = Fernet(key.encode())
        self.digest_key = digest_key.encode()
        self.db.executescript("""
          PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS factors (
            user_id TEXT PRIMARY KEY, state TEXT NOT NULL,
            secret TEXT NOT NULL, created REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS backups (
            user_id TEXT NOT NULL, digest TEXT NOT NULL,
            PRIMARY KEY(user_id, digest));
          CREATE TABLE IF NOT EXISTS used_codes (
            user_id TEXT NOT NULL, digest TEXT NOT NULL, expires REAL NOT NULL,
            PRIMARY KEY(user_id, digest));
          CREATE TABLE IF NOT EXISTS attempts (
            bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, expires REAL NOT NULL);
        """)

    def digest(self, value: str) -> str:
        return hmac.new(self.digest_key, value.encode(), hashlib.sha256).hexdigest()

    def factor(self, user_id):
        with self.lock:
            row = self.db.execute("SELECT * FROM factors WHERE user_id=?", (user_id,)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["secret"] = self.fernet.decrypt(result["secret"].encode()).decode()
            return result

    def pending(self, user_id, secret, now):
        with self.lock:
            old = self.factor(user_id)
            if old and old["state"] == "ACTIVE":
                raise AuthError("2FA ya está activo; no se permite reemplazarlo con contraseña")
            self.db.execute("INSERT OR REPLACE INTO factors VALUES (?, 'PENDING_VERIFICATION', ?, ?)",
                            (user_id, self.fernet.encrypt(secret.encode()).decode(), now))

    def rate_limit(self, bucket, now, maximum=5, seconds=300):
        with self.lock:
            self.db.execute("DELETE FROM attempts WHERE expires<=?", (now,))
            row = self.db.execute("SELECT * FROM attempts WHERE bucket=?", (bucket,)).fetchone()
            if row and row["count"] >= maximum:
                raise TooManyAttempts("Demasiados intentos; espera cinco minutos")
            self.db.execute("INSERT INTO attempts VALUES (?, 1, ?) ON CONFLICT(bucket) DO UPDATE SET count=count+1",
                            (bucket, now + seconds))

    def check_replay(self, user_id, code, now):
        with self.lock:
            self.db.execute("DELETE FROM used_codes WHERE expires<=?", (now,))
            if self.db.execute("SELECT 1 FROM used_codes WHERE user_id=? AND digest=?",
                               (user_id, self.digest(code))).fetchone():
                raise ReplayAttackDetected("ReplayAttackDetected: código ya utilizado")

    def has_backup(self, user_id, code):
        with self.lock:
            return self.db.execute("SELECT 1 FROM backups WHERE user_id=? AND digest=?",
                                   (user_id, self.digest(code))).fetchone() is not None

    def commit_code(self, user_id, code, now, backup=False, activate_codes=None):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self.check_replay(user_id, code, now)
                if backup:
                    cursor = self.db.execute("DELETE FROM backups WHERE user_id=? AND digest=?",
                                             (user_id, self.digest(code)))
                    if cursor.rowcount != 1:
                        raise AuthError("Código de respaldo inválido o utilizado")
                self.db.execute("INSERT INTO used_codes VALUES (?, ?, ?)",
                                (user_id, self.digest(code), now + 90))
                if activate_codes is not None:
                    self.db.execute("UPDATE factors SET state='ACTIVE' WHERE user_id=?", (user_id,))
                    self.db.execute("DELETE FROM backups WHERE user_id=?", (user_id,))
                    self.db.executemany("INSERT INTO backups VALUES (?, ?)",
                                        [(user_id, self.digest(c)) for c in activate_codes])
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
