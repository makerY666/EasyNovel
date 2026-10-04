import httpx
from fastapi.testclient import TestClient
from easynovel.app import create_app
from easynovel.config import Settings
from conftest import ModelFixture,project,chapter,provider,wait_run,rev
from test_workflow import start


def test_durable_author_interrupt_survives_process_restart(tmp_path):
    settings=Settings(data_dir=tmp_path,token='recovery-test',test_mode=True,legacy_path=tmp_path/'missing.db')
    fixture=ModelFixture(); headers={'Authorization':'Bearer recovery-test'}
    with TestClient(create_app(settings,httpx.MockTransport(fixture)),headers=headers) as c:
        p=project(c); ch=chapter(c,p['id']); model=provider(c); run=start(c,p,ch,model)
        assert wait_run(c,run['id'],['awaiting_plan','failed'])['status']=='awaiting_plan'
    prior_calls=len(fixture.requests)
    with TestClient(create_app(settings,httpx.MockTransport(fixture)),headers=headers) as c:
        assert c.get('/api/v1/runs/'+run['id']).json()['status']=='awaiting_plan'
        assert c.post('/api/v1/runs/'+run['id']+'/approve-plan',json={}).status_code==200
        result=wait_run(c,run['id'],['awaiting_review','failed','paused'])
        assert result['status']=='awaiting_review',result
        assert len(fixture.requests)>prior_calls
        calls=c.get('/api/v1/runs/'+run['id']+'/calls').json()
        assert len([x for x in calls if x['call_key'].startswith('architecture:')])==1
        assert c.post('/api/v1/runs/'+run['id']+'/approve',json={'expected_revision':rev(c,p['id']),'idempotency_key':'restart','accepted_memory_indices':[]}).status_code==200
        assert wait_run(c,run['id'],['completed','failed'])['status']=='completed'


def test_uncertain_paid_call_is_not_resent_on_resume(tmp_path):
    attempts=[]
    def disconnected(request):
        attempts.append(request)
        raise httpx.ReadTimeout('fixture network failure')
    settings=Settings(data_dir=tmp_path,token='uncertain-test',test_mode=True,legacy_path=tmp_path/'missing.db')
    with TestClient(create_app(settings,httpx.MockTransport(disconnected)),headers={'Authorization':'Bearer uncertain-test'}) as c:
        p=project(c); ch=chapter(c,p['id']); model=provider(c); run=start(c,p,ch,model)
        result=wait_run(c,run['id'],['failed','paused'])
        assert result['usage']['reserved_tokens']>0
        assert len(attempts)==1
        assert c.post('/api/v1/runs/'+run['id']+'/resume',json={}).status_code==200
        result=wait_run(c,run['id'],['paused','failed'])
        assert result['usage']['reserved_tokens']>0 and len(attempts)==1
        assert c.post('/api/v1/runs/'+run['id']+'/resume',json={'provider_output_limits':{model['id']:8192},'role_limits':{'architect':4096}}).status_code==200
        result=wait_run(c,run['id'],['paused','failed'])
        assert result['status']=='paused' and len(attempts)==1
        assert result['usage']['reserved_tokens']>0
