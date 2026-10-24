from concurrent.futures import ThreadPoolExecutor
import time
import jwt
import pytest
from fastapi.testclient import TestClient
from prefect.client.orchestration import get_client
from app.errors import AuthError, ReplayAttackDetected
from app.flows import dispatch, verify_flow
from app.totp import totp
from app.store import Store

SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
CREDS = {"email":"student@example.test","password":"correct-password"}
def bearer(token): return {"Authorization": "Bearer " + token}

def active(app):
    s=app.state.service
    s.store.pending("student-1",SECRET,time.time()-60)
    s.store.commit_code("student-1","activation",time.time()-60,activate_codes=["ONE-USE-BACKUP"])
    return s

def test_enrollment_state_machine_and_permissions(app):
    c=TestClient(app)
    setup=c.post('/auth/enroll/start',json=CREDS).json()
    s=app.state.service
    assert setup['state']=='PENDING_VERIFICATION'
    assert s.store.factor('student-1')['state']=='PENDING_VERIFICATION'
    assert c.get('/api/boveda-secreta',headers=bearer(setup['enrollment_token'])).status_code==401
    pre=c.post('/auth/login',json=CREDS).json()['pre_auth_token']
    assert c.post('/auth/enroll/confirm',headers=bearer(pre),json={'code':'123456'}).status_code==401
    r=c.post('/auth/enroll/confirm',headers=bearer(setup['enrollment_token']),json={'code':totp(setup['secret'])})
    assert r.status_code==200
    assert len(r.json()['backup_codes'])==8
    assert s.store.factor('student-1')['state']=='ACTIVE'
    assert c.post('/auth/enroll/start',json=CREDS).status_code==401
    raw=s.store.db.execute('SELECT secret FROM factors').fetchone()[0]
    assert raw != setup['secret']

def test_step_up_replay_and_prefect_failure_task(app):
    s=active(app); c=TestClient(app)
    pre=c.post('/auth/login',json=CREDS).json()['pre_auth_token']
    assert c.get('/api/boveda-secreta',headers=bearer(pre)).status_code==401
    payload={'code':totp(SECRET),'strategy':'totp'}
    success=c.post('/auth/verify-2fa',headers=bearer(pre),json=payload)
    assert success.status_code==200
    assert c.get('/api/boveda-secreta',headers=bearer(success.json()['access_token'])).status_code==200
    replay=c.post('/auth/verify-2fa',headers=bearer(pre),json=payload)
    assert replay.status_code==409
    assert replay.json()['error']=='ReplayAttackDetected'
    with get_client(sync_client=True) as pc:
        runs=pc.read_task_runs()
        assert any(r.name.startswith('check_anti_replay_cache') and r.state.is_failed() for r in runs)
        assert any(r.name.startswith('execute_mfa_strategy') and r.task_inputs.get('wait_for') for r in runs)
        flows=pc.read_flow_runs()
        assert any(r.state.is_failed() for r in flows)
        for flow_run in flows:
            assert set(flow_run.parameters) <= {'request_id'}

def test_backup_consumed_and_cannot_reuse_after_replay_ttl(app):
    s=active(app); c=TestClient(app); pre=s.token('student-1','pre_auth')
    r=c.post('/auth/verify-2fa',headers=bearer(pre),json={'code':'ONE-USE-BACKUP','strategy':'backup'})
    assert r.status_code==200
    assert not s.store.has_backup('student-1','ONE-USE-BACKUP')
    s.store.db.execute('DELETE FROM used_codes')
    assert c.post('/auth/verify-2fa',headers=bearer(pre),json={'code':'ONE-USE-BACKUP','strategy':'backup'}).status_code==401

def test_concurrent_replay_one_success(app):
    s=active(app); token=s.token('student-1','pre_auth'); code=totp(SECRET)
    def attempt(_):
        try:
            dispatch(verify_flow,s,token=token,code=code,strategy='totp')
            return 'ok'
        except ReplayAttackDetected:
            return 'replay'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt,range(2)))==['ok','replay']

def test_replay_survives_database_reopen(app):
    s=active(app); s.store.commit_code('student-1','123456',time.time())
    other=Store(s.settings.database,s.settings.encryption_key,s.settings.jwt_secret)
    try:
        with pytest.raises(ReplayAttackDetected): other.check_replay('student-1','123456',time.time())
    finally: other.db.close()

def test_expired_tampered_and_wrong_purpose_tokens(app):
    s=active(app)
    with pytest.raises(AuthError): s.claims(s.token('student-1','access'),'pre_auth')
    token=s.token('student-1','pre_auth')
    claims=jwt.decode(token,s.settings.jwt_secret,algorithms=['HS256'],audience='2fa-lab-api')
    claims['exp']=int(time.time())-1
    with pytest.raises(AuthError): s.claims(jwt.encode(claims,s.settings.jwt_secret,algorithm='HS256'),'pre_auth')
    with pytest.raises(AuthError): s.claims(token+'x','pre_auth')

def test_bad_credentials_and_rate_limit(app):
    s=active(app); c=TestClient(app)
    assert c.post('/auth/login',json={**CREDS,'password':'wrong'}).status_code==401
    token=s.token('student-1','pre_auth')
    for _ in range(5):
        assert c.post('/auth/verify-2fa',headers=bearer(token),json={'code':'abcdef'}).status_code==401
    assert c.post('/auth/verify-2fa',headers=bearer(token),json={'code':'abcdef'}).status_code==429
