"""Solo identificadores opacos viajan como parámetros de Prefect.

Credenciales, semillas, OTP y JWT permanecen en memoria del proceso de API.
Las tareas no devuelven secretos ni persisten resultados ni reutilizan caché.
"""
import secrets
import threading
from dotenv import load_dotenv

# Prefect snapshots settings when imported: load the local API URL first.
load_dotenv()

from prefect import flow, task, get_run_logger
from prefect.cache_policies import NO_CACHE
from .service import RequestContext

_contexts = {}
_lock = threading.Lock()
TASK = dict(cache_policy=NO_CACHE, persist_result=False, retries=0, log_prints=False)
FLOW = dict(persist_result=False, retries=0, log_prints=False)


def ctx(request_id):
    with _lock:
        return _contexts[request_id]


@task(**TASK)
def authenticate_primary(request_id):
    c = ctx(request_id)
    c.service.authenticate(c)


@task(**TASK)
def issue_pre_auth_state(request_id):
    c = ctx(request_id)
    c.service.login(c)


@task(**TASK)
def create_pending_verification(request_id):
    c = ctx(request_id)
    c.service.begin_enrollment(c)


@task(**TASK)
def activate_verified_factor(request_id):
    c = ctx(request_id)
    c.service.confirm_enrollment(c)


@task(**TASK)
def validate_pre_auth_state(request_id):
    c = ctx(request_id)
    c.service.validate_pre_auth(c)


@task(**TASK)
def check_anti_replay_cache(request_id):
    c = ctx(request_id)
    c.service.store.check_replay(c.user_id, c.values["code"], c.now)


@task(**TASK)
def execute_mfa_strategy(request_id):
    c = ctx(request_id)
    c.service.execute_strategy(c)
    label = "BackupCodeStrategy" if c.window is None else {0: "C", -1: "C-1", 1: "C+1"}[c.window]
    get_run_logger().info("Segundo factor validado: %s", label)


@task(**TASK)
def issue_elevated_session(request_id):
    c = ctx(request_id)
    c.service.issue(c)


@flow(name="login", **FLOW)
def login_flow(request_id):
    authenticate_primary(request_id)
    issue_pre_auth_state(request_id)


@flow(name="aprovisionamiento-pending", **FLOW)
def enrollment_flow(request_id):
    authenticate_primary(request_id)
    with ctx(request_id).service.gate:
        create_pending_verification(request_id)


@flow(name="aprovisionamiento-active", **FLOW)
def confirm_flow(request_id):
    with ctx(request_id).service.gate:
        activate_verified_factor(request_id)


@flow(name="verificar-segundo-factor", **FLOW)
def verify_flow(request_id):
    with ctx(request_id).service.gate:
        previous = []
        for step in (validate_pre_auth_state, check_anti_replay_cache,
                     execute_mfa_strategy, issue_elevated_session):
            state = step(request_id, wait_for=previous, return_state=True)
            state.result()  # Propaga el error original y detiene el flow.
            previous = [state]  # Dependencias explícitas para el grafo de Prefect.


def dispatch(flow_fn, service, **values):
    request_id = secrets.token_hex(16)
    context = RequestContext(service=service, values=values)
    with _lock:
        _contexts[request_id] = context
    try:
        flow_fn(request_id)
        return context.output
    finally:
        with _lock:
            del _contexts[request_id]
