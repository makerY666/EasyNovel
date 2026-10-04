import time
import uuid
from conftest import project,chapter,provider,wait_run,rev


def start(c,p,ch,model,budget=200000):
    r=c.post(f'/api/v1/projects/{p["id"]}/runs',json={'chapter_id':ch['id'],'task':'让林舟发现玉佩，增加关系冲突','provider_id':model['id'],'token_budget':budget})
    assert r.status_code==200,r.text
    return r.json()


def test_full_director_workflow_and_selected_memory(studio):
    c,_,fixture=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    r=start(c,p,ch,model)
    plan=wait_run(c,r['id'],['awaiting_plan','failed','paused'])
    assert plan['status']=='awaiting_plan',plan
    assert c.post(f'/api/v1/runs/{r["id"]}/approve-plan',json={'plan_index':0}).status_code==200
    draft=wait_run(c,r['id'],['awaiting_review','failed','paused'])
    assert draft['status']=='awaiting_review',draft
    assert len(draft['artifacts']['memory_delta'])==1
    assert not c.get(f'/api/v1/projects/{p["id"]}/records').json()
    assert c.post(f'/api/v1/runs/{r["id"]}/approve',json={'accepted_memory_indices':[0],'expected_revision':rev(c,p['id']),'idempotency_key':str(uuid.uuid4())}).status_code==200
    done=wait_run(c,r['id'],['completed','failed','stale'])
    assert done['status']=='completed',done
    assert c.get(f'/api/v1/projects/{p["id"]}/records').json()[0]['status']=='confirmed'
    assert done['usage']['reserved_tokens']==0
    assert all('never-return-this-secret' not in x['prompt'] for x in c.get(f'/api/v1/runs/{r["id"]}/calls').json())


def test_budget_pause_before_payment_and_resume(studio):
    c,_,fixture=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    r=start(c,p,ch,model,100)
    paused=wait_run(c,r['id'],['paused','failed'])
    assert paused['status']=='paused' and not fixture.requests
    c.post(f'/api/v1/runs/{r["id"]}/resume',json={'token_budget':200000})
    resumed=wait_run(c,r['id'],['awaiting_plan','failed','paused'])
    assert resumed['status']=='awaiting_plan',resumed


def test_critical_review_requires_reason_and_bounded_revisions(studio):
    c,_,fixture=studio; fixture.critical=True
    p=project(c); ch=chapter(c,p['id']); model=provider(c); r=start(c,p,ch,model)
    assert wait_run(c,r['id'],['awaiting_plan','failed'])['status']=='awaiting_plan'
    c.post(f'/api/v1/runs/{r["id"]}/approve-plan',json={})
    result=wait_run(c,r['id'],['awaiting_review','failed','paused'])
    assert result['status']=='awaiting_review',result
    assert result['artifacts']['revision_round']==2
    approve=c.post(f'/api/v1/runs/{r["id"]}/approve',json={'expected_revision':rev(c,p['id']),'idempotency_key':'critical'})
    assert approve.status_code==409
    assert c.post(f'/api/v1/runs/{r["id"]}/approve',json={'expected_revision':rev(c,p['id']),'idempotency_key':'critical','override_reason':'作者有意保留歧义'}).status_code==200
    assert wait_run(c,r['id'],['completed','failed'])['status']=='completed'


def test_stale_run_preserves_artifacts(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c); r=start(c,p,ch,model)
    wait_run(c,r['id'],['awaiting_plan'])
    c.post(f'/api/v1/projects/{p["id"]}/records',json={'kind':'rule','title':'新规则','content':'改变创作依据','status':'confirmed'})
    c.post(f'/api/v1/runs/{r["id"]}/approve-plan',json={})
    result=wait_run(c,r['id'],['stale','failed'])
    assert result['status']=='stale' and result['artifacts']['plans']


def test_http_rejection_no_sensitive_diagnostics(studio):
    c,_,fixture=studio; fixture.reject=True
    p=project(c); ch=chapter(c,p['id']); model=provider(c); r=start(c,p,ch,model)
    result=wait_run(c,r['id'],['failed'])
    assert result['usage']['reserved_tokens']==0
    assert 'secret should never persist' not in str(result)


def test_money_budget_unknown_price_blocks_call(studio):
    c,_,fixture=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    r=c.post(f'/api/v1/projects/{p["id"]}/runs',json={'chapter_id':ch['id'],'task':'写正文','provider_id':model['id'],'token_budget':100000,'money_budget':1}).json()
    assert wait_run(c,r['id'],['paused'])['status']=='paused'
    assert not fixture.requests


def test_one_writer_and_manual_review_edit_regenerates_memory(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c); r=start(c,p,ch,model)
    wait_run(c,r['id'],['awaiting_plan'])
    duplicate=c.post(f'/api/v1/projects/{p["id"]}/runs',json={'chapter_id':ch['id'],'task':'另一候选','provider_id':model['id'],'token_budget':200000})
    assert duplicate.status_code==409
    c.post(f'/api/v1/runs/{r["id"]}/approve-plan',json={})
    before=wait_run(c,r['id'],['awaiting_review'])
    assert c.post(f'/api/v1/runs/{r["id"]}/edit',json={'draft':'林舟拾起玉佩。\n\n玉佩的名字被擦掉了。'}).status_code==200
    after=wait_run(c,r['id'],['awaiting_review','stale','failed'])
    assert after['status']=='awaiting_review',after
    assert after['artifacts']['version_id']!=before['artifacts']['version_id']


def test_chapter_cumulative_budget_is_isolated(studio):
    c,_,fixture=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    other=chapter(c,p['id'])
    assert c.patch('/api/v1/projects/'+p['id'],json={'expected_revision':rev(c,p['id']),'settings':{'chapter_token_budget':90000}}).status_code==200
    from easynovel.database import Run
    app=studio[1]
    with app.state.db.write() as s:
        s.add(Run(project_id=p['id'],chapter_id=ch['id'],status='completed',input_revision=rev(c,p['id']),request={},usage={'input_tokens':90000,'output_tokens':0,'reserved_tokens':0,'cost':0}))
    first=start(c,p,ch,model)
    assert wait_run(c,first['id'],['paused'])['status']=='paused'
    assert not fixture.requests
    assert '本章累计' in c.get('/api/v1/runs/'+first['id']).json()['error']
    second=start(c,p,other,model)
    assert wait_run(c,second['id'],['awaiting_plan','paused'])['status']=='awaiting_plan'
