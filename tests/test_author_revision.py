import uuid
from conftest import project,chapter,provider,wait_run,rev,save
from test_generation_limits import run_body
from easynovel.database import Chapter,Run


def initial(c,p,ch,model):
    r=c.post('/api/v1/projects/'+p['id']+'/runs',json=run_body(ch,model,auto_approve_plan=True)).json()
    result=wait_run(c,r['id'],['awaiting_review','failed','paused'])
    assert result['status']=='awaiting_review',result
    return result


def test_author_revision_replaces_candidate_keeps_history_and_needs_approval(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    before=initial(c,p,ch,model)
    response=c.post('/api/v1/runs/'+before['id']+'/revise',json={'instruction':'突出人物犹豫，不改玉佩事件','expected_revision':rev(c,p['id'])})
    assert response.status_code==200,response.text
    run=response.json(); result=wait_run(c,run['id'],['awaiting_review','failed','paused','stale'])
    assert result['status']=='awaiting_review',result
    assert run['request']['kind']=='author_revision'
    assert c.get('/api/v1/runs/'+before['id']).json()['status']=='cancelled'
    assert c.get('/api/v1/versions/'+before['artifacts']['version_id']).status_code==200
    assert result['artifacts']['version_id']!=before['artifacts']['version_id']
    assert c.get('/api/v1/chapters/'+ch['id']).json()['confirmed_version_id'] is None
    assert not c.get('/api/v1/projects/'+p['id']+'/records').json()
    assert c.post('/api/v1/runs/'+run['id']+'/approve',json={'expected_revision':rev(c,p['id']),'idempotency_key':str(uuid.uuid4()),'accepted_memory_indices':[0]}).status_code==200
    assert wait_run(c,run['id'],['completed','failed','stale'])['status']=='completed'


def test_completed_prose_revision_and_stale_source_rejection(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    before=initial(c,p,ch,model)
    c.post('/api/v1/runs/'+before['id']+'/approve',json={'expected_revision':rev(c,p['id']),'idempotency_key':'first'})
    assert wait_run(c,before['id'],['completed','failed'])['status']=='completed'
    run=c.post('/api/v1/runs/'+before['id']+'/revise',json={'instruction':'压缩重复描写','expected_revision':rev(c,p['id'])}).json()
    result=wait_run(c,run['id'],['awaiting_review','failed','paused'])
    assert result['status']=='awaiting_review',result
    assert c.get('/api/v1/chapters/'+ch['id']).json()['confirmed_version_id']==before['artifacts']['version_id']
    assert result['artifacts']['impact']
    stale=c.post('/api/v1/runs/'+before['id']+'/revise',json={'instruction':'旧稿修改','expected_revision':rev(c,p['id'])})
    assert stale.status_code==409


def test_stale_project_revision_does_not_cancel_parent(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    before=initial(c,p,ch,model)
    rejected=c.post('/api/v1/runs/'+before['id']+'/revise',json={'instruction':'修改','expected_revision':0})
    assert rejected.status_code==409
    assert c.get('/api/v1/runs/'+before['id']).json()['status']=='awaiting_review'


def test_author_revision_respects_new_manual_draft(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    before=initial(c,p,ch,model)
    manual=save(c,ch,p['id'],'作者的新草稿')
    rejected=c.post('/api/v1/runs/'+before['id']+'/revise',json={'instruction':'压缩','expected_revision':rev(c,p['id'])})
    assert rejected.status_code==409
    assert c.get('/api/v1/chapters/'+ch['id']).json()['draft_version_id']==manual['id']


def test_impacted_chapter_can_be_repaired_but_not_continued(studio):
    c,app,_=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    before=initial(c,p,ch,model)
    c.post('/api/v1/runs/'+before['id']+'/approve',json={'expected_revision':rev(c,p['id']),'idempotency_key':'original'})
    assert wait_run(c,before['id'],['completed','failed'])['status']=='completed'
    with app.state.db.write() as s: s.get(Chapter,ch['id']).blocked=True
    rejected=c.post('/api/v1/projects/'+p['id']+'/runs',json=run_body(ch,model,auto_approve_plan=True))
    assert rejected.status_code==409
    repaired=c.post('/api/v1/runs/'+before['id']+'/revise',json={'instruction':'依照前文变化修复本章','expected_revision':rev(c,p['id'])})
    assert repaired.status_code==200,repaired.text
    result=wait_run(c,repaired.json()['id'],['awaiting_review','failed','paused','stale'])
    assert result['status']=='awaiting_review',result
    assert c.get('/api/v1/chapters/'+ch['id']).json()['blocked'] is True
    response=c.post('/api/v1/runs/'+result['id']+'/approve',json={'expected_revision':rev(c,p['id']),'idempotency_key':'reviewed-repair'})
    assert response.status_code==200,response.text
    assert wait_run(c,result['id'],['completed','failed','stale'])['status']=='completed'
    assert c.get('/api/v1/chapters/'+ch['id']).json()['blocked'] is False


def test_stale_candidate_is_revised_with_fresh_context(studio):
    c,app,_=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    before=initial(c,p,ch,model)
    c.post('/api/v1/projects/'+p['id']+'/chapters',json={'title':'新章节'})
    with app.state.db.write() as s: s.get(Run,before['id']).status='stale'
    response=c.post('/api/v1/runs/'+before['id']+'/revise',json={'instruction':'根据当前前文重新审改，压缩到800字','expected_revision':rev(c,p['id'])})
    assert response.status_code==200,response.text
    current=response.json()
    assert current['input_revision']>before['input_revision']
    assert current['request']['target_chars']==800
    result=wait_run(c,current['id'],['awaiting_review','failed','paused','stale'])
    assert result['status']=='awaiting_review',result
