"""Completa claves vacías sin imprimirlas ni reemplazar claves existentes."""
from pathlib import Path
import secrets
from cryptography.fernet import Fernet

path = Path('.env')
if not path.exists():
    raise SystemExit('Primero copia .env.example a .env')
content = path.read_text()
for name, generator in [('JWT_SECRET', lambda: secrets.token_urlsafe(48)),
                         ('MFA_ENCRYPTION_KEY', lambda: Fernet.generate_key().decode())]:
    lines = content.splitlines()
    prefix = name + '='
    if not any(line.startswith(prefix) for line in lines):
        lines.append(prefix + generator())
    else:
        lines = [prefix + generator() if line == prefix else line for line in lines]
    content = '\n'.join(lines) + '\n'
path.write_text(content)
path.chmod(0o600)
print('Claves locales configuradas. Conserva .env fuera de Git.')
