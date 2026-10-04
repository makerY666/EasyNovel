import uuid
from conftest import project,chapter,rev,save,commit


def test_auth_and_secret(studio):
    c,_,_=studio
    assert c.get('/api/v1/health',headers={'Authorization':'Bearer wrong'}).status_code==401
    p=c.post('/api/v1/providers',json={'name':'模型','base_url':'https://api.example/v1','model':'m','api_key':'secret'}).json()
    assert p['has_key'] and 'secret' not in c.get('/api/v1/providers').text
    assert c.post('/api/v1/providers',json={'name':'bad','base_url':'https://user:pass@example/v1','model':'m'}).status_code==422


def test_draft_not_canon_atomic_commit_idempotency(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id']); v=save(c,ch,p['id'],'林舟拾起玉佩。')
    assert not c.get(f'/api/v1/projects/{p["id"]}/search?q=玉佩').json()['items']
    body={'version_id':v['id'],'expected_revision':rev(c,p['id']),'idempotency_key':'same','memory_delta':[{'kind':'event','title':'玉佩','content':'林舟拾起玉佩','source_type':'text','source_version_id':v['id'],'source_paragraph_id':v['paragraphs'][0]['id']} ]}
    a=c.post(f'/api/v1/chapters/{ch["id"]}/commit',json=body)
    assert a.status_code==200,a.text
    b=c.post(f'/api/v1/chapters/{ch["id"]}/commit',json=body)
    assert b.json()==a.json()
    assert len(c.get(f'/api/v1/projects/{p["id"]}/records').json())==1
    changed={**body,'override_reason':'different'}
    assert c.post(f'/api/v1/chapters/{ch["id"]}/commit',json=changed).status_code==409


def test_commit_rolls_back_on_invalid_memory(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id']); v=save(c,ch,p['id'],'林舟拾起玉佩。')
    before=rev(c,p['id'])
    r=commit(c,ch,p['id'],v,memory_delta=[{'kind':'event','title':'事件','content':'候选','source_type':'text','source_version_id':v['id'],'source_paragraph_id':'missing'}])
    assert r.status_code==422
    assert rev(c,p['id'])==before
    assert c.get('/api/v1/chapters/'+ch['id']).json()['confirmed'] is None


def test_temporal_pov_and_plans_separate(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id'],story_time=5)
    url=f'/api/v1/projects/{p["id"]}/records'
    for item in [
        {'kind':'knowledge','title':'林舟知道暗门','content':'知道暗门','valid_from':4,'data':{'character_id':'林舟'}},
        {'kind':'knowledge','title':'未来秘密','content':'第十天知道凶手','valid_from':10,'data':{'character_id':'林舟'}},
        {'kind':'knowledge','title':'另一个人秘密','content':'仅苏雨知道','valid_from':3,'data':{'character_id':'苏雨'}},
        {'kind':'plan','title':'未来背叛','content':'未来计划背叛','data':{'level':'book'}},
        {'kind':'event','title':'候选事件','content':'不应读取'}]:
        item['status']='candidate' if item['title']=='候选事件' else 'confirmed'
        assert c.post(url,json=item).status_code==200
    result=c.post(f'/api/v1/projects/{p["id"]}/context',json={'chapter_id':ch['id'],'task':'秘密','pov':'林舟'}).json()
    assert [r['title'] for r in result['character_knowledge']]==['林舟知道暗门']
    assert result['plans'][0]['title']=='未来背叛'
    assert all(r['kind']!='plan' for r in result['evidence'])
    assert '候选事件' not in str(result)


def test_long_range_foreshadow_and_alias(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id'],number=2300)
    for item in [
        {'kind':'foreshadow','title':'第十八章的玉佩','content':'刻痕与失踪父亲有关','data':{'introduced_chapter':18,'payoff_start':2200,'status':'open'}},
        {'kind':'character','title':'林舟','content':'寻找父亲','data':{'aliases':['小舟']}}]:
        assert c.post(f'/api/v1/projects/{p["id"]}/records',json={**item,'status':'confirmed'}).status_code==200
    result=c.post(f'/api/v1/projects/{p["id"]}/context',json={'chapter_id':ch['id'],'task':'小舟进入古城'}).json()
    assert any(r['title']=='第十八章的玉佩' for r in result['evidence'])
    assert any(r['title']=='林舟' for r in result['evidence'])


def test_hard_context_overflow_not_silently_dropped(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id'])
    c.post(f'/api/v1/projects/{p["id"]}/records',json={'kind':'rule','title':'硬规则','content':'长规则'*300,'status':'confirmed'})
    r=c.post(f'/api/v1/projects/{p["id"]}/context',json={'chapter_id':ch['id'],'token_limit':256})
    assert r.status_code==409


def test_retroactive_edit_blocks_successors_and_stale_commit(studio):
    c,_,_=studio; p=project(c); a=chapter(c,p['id']); b=chapter(c,p['id'])
    v=save(c,a,p['id'],'林舟读过信件。'); assert commit(c,a,p['id'],v).status_code==200
    new=save(c,a,p['id'],'林舟没有读过信件。')
    assert commit(c,a,p['id'],new,'change').status_code==409
    impact=c.post(f'/api/v1/chapters/{a["id"]}/impact',json={'version_id':new['id'],'expected_revision':rev(c,p['id'])}).json()
    assert impact['items'][0]['chapter_id']==b['id']
    assert commit(c,a,p['id'],new,'change').status_code==200
    assert c.get('/api/v1/chapters/'+b['id']).json()['blocked']
    assert c.post(f'/api/v1/projects/{p["id"]}/context',json={'chapter_id':b['id']}).status_code==409
    r=c.post(f'/api/v1/impact/{impact["id"]}/resolve',json={'chapter_ids':[b['id']],'expected_revision':rev(c,p['id']),'reason':'已人工核查'})
    assert r.status_code==200
    assert not c.get('/api/v1/chapters/'+b['id']).json()['blocked']


def test_branch_copy_sources_and_isolation(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id']); v=save(c,ch,p['id'],'玉佩属于林舟。')
    assert commit(c,ch,p['id'],v).status_code==200
    c.post(f'/api/v1/projects/{p["id"]}/records',json={'kind':'event','title':'所有权','content':'林舟持有玉佩','status':'confirmed','source_type':'text','source_version_id':v['id']})
    b=c.post(f'/api/v1/projects/{p["id"]}/branches',json={'name':'另一选择'}).json()
    branch_records=c.get(f'/api/v1/projects/{p["id"]}/records?branch_id={b["id"]}').json()
    assert branch_records[0]['source_version_id']!=v['id']
    c.post(f'/api/v1/projects/{p["id"]}/records',json={'kind':'rule','title':'独立设定','content':'只在分支出现','status':'confirmed','branch_id':b['id']})
    assert '独立设定' not in c.get(f'/api/v1/projects/{p["id"]}/records').text


def test_locked_ai_paragraph_and_source_validation(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id'])
    v=save(c,ch,p['id'],'锁定内容',paragraphs=[{'id':'stable','text':'锁定内容','locked':True}])
    r=c.post(f'/api/v1/chapters/{ch["id"]}/versions',json={'content':'擅自改变','source':'ai','expected_revision':rev(c,p['id'])})
    assert r.status_code==409
    c.post(f'/api/v1/projects/{p["id"]}/records',json={'kind':'event','title':'草稿记忆','content':'锁定内容','source_type':'text','source_version_id':v['id']})
    r=c.post(f'/api/v1/projects/{p["id"]}/records',json={'kind':'event','title':'越过确认','content':'锁定内容','source_type':'text','source_version_id':v['id'],'status':'confirmed'})
    assert r.status_code==409
