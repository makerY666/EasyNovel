import json
import time
import httpx
import pytest
from fastapi.testclient import TestClient
from easynovel.app import create_app
from easynovel.config import Settings


class ModelFixture:
    def __init__(self): self.requests=[]; self.reject=False; self.critical=False

    def __call__(self,request):
        self.requests.append(request)
        if self.reject: return httpx.Response(429,json={'error':{'message':'secret should never persist'}})
        body=json.loads(request.content)
        prompt=body.get('messages',[{},{}])[-1].get('content','')
        if request.url.path.endswith('/embeddings'):
            return httpx.Response(200,json={'data':[{'index':i,'embedding':[float(len(t)%17),1.0,0.5]} for i,t in enumerate(body['input'])],'usage':{'prompt_tokens':10}})
        if '"title": "PlansOutput"' in prompt:
            output={'plans':[{'title':'旧玉佩','goal':'发现前文线索','scenes':[{'pov':'林舟','goal':'查明真相','obstacle':'守卫阻拦','action':'谈判','turn':'认出玉佩','cause':'曾见过刻痕','cost':'失去信任','state_changes':['关系紧张']}]}]}
        elif '"title": "DraftOutput"' in prompt:
            output={'content':'林舟拾起玉佩。\n\n玉佩上刻着旧时的名字。','plan_changed':False}
        elif '"title": "ReviewOutput"' in prompt:
            output={'issues':[{'severity':'critical','category':'motivation','description':'动机需要补充','suggestion':'说明代价','basis':'missing_cause','quote':'林舟拾起玉佩。'}] if self.critical else [],'summary':'已核查人物动机和证据'}
        elif '"title": "IssueVerdicts"' in prompt:
            output={'verdicts':[{'issue_index':0,'verdict':'confirmed','reason':'正文存在可定位的关键问题'}]}
        elif '"title": "MemoryOutput"' in prompt:
            output={'records':[{'kind':'event','title':'拾起玉佩','content':'林舟拾起玉佩','quote':'林舟拾起玉佩。','entity_ids':['林舟']},{'kind':'event','title':'虚构引用','content':'不存在的事实','quote':'这句话不在正文'}]}
        elif '"title": "RecordInput"' in prompt:
            output={'kind':'directive','title':'关系决裂','content':'本卷逐渐决裂，但不公开背叛','data':{'scope':'book','hard':True}}
        else: output={'ok':True}
        content=json.dumps(output,ensure_ascii=False)
        return httpx.Response(200,json={'choices':[{'message':{'content':content}}],'usage':{'prompt_tokens':50,'completion_tokens':50}})


@pytest.fixture
def studio(tmp_path):
    fixture=ModelFixture()
    settings=Settings(data_dir=tmp_path/'data',token='test-token',test_mode=True,legacy_path=tmp_path/'absent.db')
    app=create_app(settings,httpx.MockTransport(fixture))
    with TestClient(app,headers={'Authorization':'Bearer test-token'}) as client:
        yield client,app,fixture


def project(client):
    response=client.post('/api/v1/projects',json={'title':'玉佩往事','mode':'serial'})
    assert response.status_code==200,response.text
    return response.json()


def chapter(client,pid,number=None,story_time=None):
    body={'title':'线索'}
    if number: body['number']=number
    if story_time is not None: body['story_time']=story_time
    return client.post(f'/api/v1/projects/{pid}/chapters',json=body).json()


def rev(client,pid): return client.get('/api/v1/projects/'+pid).json()['revision']


def save(client,c,pid,content,**kwargs):
    r=client.post(f'/api/v1/chapters/{c["id"]}/versions',json={'content':content,'expected_revision':rev(client,pid),**kwargs})
    assert r.status_code==200,r.text
    return r.json()


def commit(client,c,pid,v,key='commit',**kwargs):
    return client.post(f'/api/v1/chapters/{c["id"]}/commit',json={'version_id':v['id'],'expected_revision':rev(client,pid),'idempotency_key':key,**kwargs})


def provider(client):
    return client.post('/api/v1/providers',json={'name':'测试模型','base_url':'https://fixture.invalid/v1','model':'test','api_key':'never-return-this-secret','embedding_model':'test-embed','max_output':1024}).json()


def wait_run(client,rid,statuses,timeout=10):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        run=client.get('/api/v1/runs/'+rid).json()
        if run['status'] in statuses: return run
        time.sleep(0.03)
    raise AssertionError(f'run did not settle: {run}')
