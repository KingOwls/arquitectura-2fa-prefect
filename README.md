# Arquitectura 2FA con TOTP y Prefect

Laboratorio de autenticación escalonada: un login web valida usuarios con Supabase Auth, una app propia genera TOTP sin conexión y FastAPI verifica el segundo factor mediante tareas observables en Prefect. El código implementa RFC 4226/6238 usando únicamente HMAC-SHA1 como primitiva criptográfica; no utiliza bibliotecas que calculen TOTP.

## Componentes

| Carpeta | Contenido |
| --- | --- |
| `mobile-authenticator/` | React Native con Expo, TOTP propio, ingreso Base32/URI, contador y SecureStore |
| `backend-prefect/` | FastAPI, patrones de estado y Strategy, JWT separados, flujos Prefect y pruebas |
| `web-login/` | Login, aprovisionamiento QR, verificación, bóveda y controles de demostración |
| `docs/` | Especificaciones, arquitectura, pruebas y guion de sustentación |

## Ejecutar en Linux

Requisitos: Python 3.12, Node.js 24 LTS, npm, un proyecto Supabase activo y un usuario confirmado en **Authentication → Users**. Para pruebas móviles usa Android físico con Expo Go compatible con SDK 58, o un emulador Android de Android Studio. El navegador permite revisar el Authenticator en Linux; no sustituye la evidencia móvil.

### 1. Instalar el backend

```bash
git clone https://github.com/KingOwls/arquitectura-2fa-prefect.git
cd arquitectura-2fa-prefect/backend-prefect
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
cp .env.example .env
python scripts/generate_keys.py
```

El último comando completa las dos claves locales si están vacías. Edita `.env` y configura `SUPABASE_URL` y `SUPABASE_PUBLISHABLE_KEY` desde el panel de tu proyecto. No uses `service_role`. No publiques `.env` ni `data/`. El repositorio incluye archivos de ejemplo sin credenciales reales.

Las cuentas se crean desde el panel de Supabase Auth; la web no registra cuentas ni envía correos. Usa un usuario de laboratorio con correo confirmado. Supabase conserva usuarios y contraseñas; SQLite local conserva la configuración MFA cifrada, los hashes de códigos de respaldo y el historial anti-replay.

### 2. Iniciar Prefect — terminal A

Desde `backend-prefect`, con el entorno virtual activo:

```bash
PREFECT_SERVER_ANALYTICS_ENABLED=false prefect server start --host 127.0.0.1
```

Dashboard: <http://127.0.0.1:4200>. No hace falta crear deployments ni workers: el backend ejecuta los flows directamente contra el servidor local.

### 3. Iniciar FastAPI — terminal B

```bash
cd arquitectura-2fa-prefect/backend-prefect
source .venv/bin/activate
uvicorn app.api:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

Abre <http://127.0.0.1:8000>. OpenAPI: <http://127.0.0.1:8000/docs>.

**Usar un solo worker es obligatorio en esta PoC**: un bloqueo en el proceso mantiene atómicos el chequeo, la validación y el consumo. No inicies dos procesos de API contra la misma base. La persistencia SQLite conserva los códigos consumidos al reiniciar el proceso.

### 4. Iniciar el Authenticator — terminal C

```bash
cd arquitectura-2fa-prefect/mobile-authenticator
npm ci
npm start
```

Abre el QR de **Expo** con Expo Go, o pulsa `a` si tienes un emulador Android iniciado. Este QR carga la aplicación; es diferente al QR **TOTP** que muestra el backend.

Para una vista de escritorio desde Linux:

```bash
npm run web
```

El ingreso manual de semilla cumple la alternativa permitida en la guía. No se implementa cámara propia: puedes pegar Base32 o la URI `otpauth://totp/...`. En Android se conserva con SecureStore; la vista web mantiene la semilla únicamente en memoria.

## Primer recorrido

1. En la web, ingresa correo y contraseña y pulsa **Configurar 2FA por primera vez**.
2. El estado queda `PENDING_VERIFICATION`. Copia la semilla a nuestra app. Escanea el QR TOTP con Google o Microsoft Authenticator para comparar.
3. Envía un código en **Confirmar activación**. El estado pasa a `ACTIVE`; guarda los ocho códigos de respaldo, visibles una sola vez.
4. Espera al siguiente código: el usado para activar también se marca consumido.
5. Inicia sesión: la contraseña solo entrega un `pre_auth_token` de cinco minutos. Envía el TOTP para obtener acceso a la bóveda.
6. En **Pruebas del laboratorio**, repite el código. Recibirás `409 ReplayAttackDetected`; Prefect mostrará el fallo en `check_anti_replay_cache`.

Para el ensayo de modo avión, carga previamente la app en Expo Go y mantenla abierta antes de desconectar el teléfono. Espera un cambio de código y escríbelo en el navegador del PC, que permanece conectado. Un APK autónomo es opcional: `npx expo run:android --variant release` requiere Java y Android SDK configurados. La exportación JS de CI no es un APK.

## Pruebas automatizadas

```bash
cd backend-prefect
source .venv/bin/activate
python -m pytest tests -q
```

Pytest levanta un Prefect temporal independiente. No necesita usuarios reales ni credenciales de Supabase: el proveedor de identidad se sustituye solo en las pruebas. Se verifica criptografía RFC, estado, tokens, códigos de respaldo, rate limit, replay concurrente, persistencia y el fallo real de tarea en Prefect.

```bash
cd mobile-authenticator
npm ci
npm test
npm run lint
npm run typecheck
npm run export:android
npm run export:web
```

GitHub Actions ejecuta estas verificaciones. Consulta [la matriz de aceptación](docs/pruebas.md) para distinguir pruebas automáticas de evidencias manuales pendientes.

## Video de solución y sustentación

**Enlace del video: pendiente de grabación y publicación.**

Aquí se añadirá el enlace real del video, junto con autoría y fecha. No se entrega una grabación simulada como evidencia. El [guion de cinco minutos](docs/video-sustentacion.md) incluye los cuatro ensayos exigidos, las pantallas que se deben mostrar y una plantilla para registrar el enlace y sus marcas de tiempo.

## Documentación

- [Especificaciones y rúbrica](docs/especificaciones.md)
- [Arquitectura y decisiones](docs/arquitectura.md)
- [Plan de pruebas y evidencias](docs/pruebas.md)
- [Video y sustentación](docs/video-sustentacion.md)
- [Resultados de verificación y dependencias](docs/verificacion.md)

## Alcance

PoC académica local. El acceso elevado dura 15 minutos; no hay revocación central ni recuperación de cuenta completa. Cinco intentos MFA por usuario cada cinco minutos y veinte intentos de contraseña por correo cada cinco minutos limitan el ensayo. No se usa MFA nativo de Supabase porque el objetivo es implementar TOTP y su orquestación desde cero. Los tokens propios protegen únicamente esta API; no son tokens Supabase ni modifican sus políticas RLS. La API necesita internet para validar la contraseña; la generación móvil TOTP no lo necesita.

Referencias: [RFC 6238](https://www.rfc-editor.org/rfc/rfc6238), [RFC 4226](https://www.rfc-editor.org/rfc/rfc4226), [Expo en Linux](https://docs.expo.dev/get-started/create-a-project/), [Prefect](https://docs.prefect.io/v3/get-started), [Supabase Auth](https://supabase.com/docs/guides/auth/passwords).
