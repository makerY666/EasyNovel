import time
from conftest import project,chapter,rev,save,commit,provider,wait_run
from easynovel.storage import Storage,decode_novel,split_novel
from easynovel.database import Job


def test_encoding_preview_pause_and_import(studio):
    c,_,_=studio; p=project(c)
    source='序言\n\n第一章 玉佩\n林舟得到玉佩。\n\n第二章 信件\n苏雨收到信件。'
    r=c.post('/api/v1/imports/preview',files={'file':('长篇.txt',source.encode('gb18030'),'text/plain')})
    assert r.status_code==200,r.text
    data=r.json(); assert len(data['chapters'])==3 and data['encoding']=='gb18030'
    job=c.post(f'/api/v1/projects/{p["id"]}/imports',json={'chapters':data['chapters']}).json()
    for _ in range(100):
        status=c.get('/api/v1/imports/'+job['id']).json()
        if status['status'] in ('completed','failed'): break
        time.sleep(0.01)
    assert status['completed']==3
    assert '林舟得到玉佩' in c.get(f'/api/v1/projects/{p["id"]}/search?q=玉佩').text
    assert c.get(f'/api/v1/projects/{p["id"]}/records').json()==[]
    model=provider(c)
    run=c.post(f'/api/v1/projects/{p["id"]}/imports/analyze',json={'provider_id':model['id'],'token_budget':200000}).json()
    assert wait_run(c,run['id'],['completed','failed'])['status']=='completed'
    assert all(r['status']=='candidate' for r in c.get(f'/api/v1/projects/{p["id"]}/records').json())


def test_backup_restore_and_confirmed_export(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id']); v=save(c,ch,p['id'],'已确认正文')
    assert commit(c,ch,p['id'],v).status_code==200
    backup=c.post('/api/v1/backups',json={}).json()
    assert c.get(f'/api/v1/backups/{backup["id"]}/download').content[:2]==b'PK'
    extra=chapter(c,p['id']); save(c,extra,p['id'],'不能导出的草稿')
    assert '不能导出的草稿' not in c.get(f'/api/v1/projects/{p["id"]}/export').text
    r=c.post(f'/api/v1/backups/{backup["id"]}/restore',json={'confirmation':'RESTORE'})
    assert r.status_code==200,r.text
    assert c.get(f'/api/v1/projects/{p["id"]}/chapters').json()['total']==1


def test_lancedb_index_separate_models(studio):
    c,_,_=studio; p=project(c); ch=chapter(c,p['id']); v=save(c,ch,p['id'],'林舟拾起玉佩。')
    commit(c,ch,p['id'],v)
    model=provider(c)
    assert c.post(f'/api/v1/projects/{p["id"]}/index',json={'provider_id':model['id']}).status_code==422
    job=c.post(f'/api/v1/projects/{p["id"]}/index',json={'provider_id':model['id'],'token_budget':100000}).json()
    for _ in range(1000):
        data=c.get('/api/v1/index/'+job['id']).json()
        if data['status'] in ('completed','failed'): break
        time.sleep(0.02)
    assert data['status']=='completed',data
    result=c.post(f'/api/v1/projects/{p["id"]}/search',json={'q':'古物','token_budget':10000}).json()
    assert result['semantic_search'] and result['items']


def test_pending_import_reserves_numbers_and_restores_job(studio,monkeypatch):
    c,app,_=studio; p=project(c); pid=p['id']
    with app.state.db.write() as s:
        job=Job(project_id=pid,kind='import',status='paused',total=3,payload={'branch_id':'main','first_number':1,'chapters':[{'title':str(i),'content':f'原文{i}'} for i in range(1,4)]})
        s.add(job); s.flush(); jid=job.id
        s.add(Job(project_id=pid,kind='index',total=1,payload={}))
    assert chapter(c,pid)['number']==4
    conflict=c.post(f'/api/v1/projects/{pid}/chapters',json={'title':'不占用导入','number':2})
    assert conflict.status_code==409 and '预留' in conflict.text
    # Persist another queued import without racing the asynchronous importer.
    monkeypatch.setattr(Storage,'schedule',lambda self,_:None)
    other=c.post(f'/api/v1/projects/{pid}/imports',json={'chapters':[{'title':'后续','content':'后续原文'}]}).json()
    with app.state.db.read() as s:
        assert s.get(Job,other['id']).payload['first_number']==5
    jobs=c.get(f'/api/v1/projects/{pid}/imports').json()
    assert len(jobs)==2 and all('payload' not in j for j in jobs)
    assert next(j for j in jobs if j['id']==jid)['status']=='paused'
    branch=c.post(f'/api/v1/projects/{pid}/branches',json={'name':'其他分支'}).json()
    assert c.get(f'/api/v1/projects/{pid}/imports',params={'branch_id':branch['id']}).json()==[]
    # Resume the saved range; manual chapter 4 and the next import remain intact.
    import asyncio
    with app.state.db.write() as s: s.get(Job,jid).status='queued'
    asyncio.run(Storage(app.state.db,app.state.settings).import_job(jid))
    restored=c.get('/api/v1/imports/'+jid).json()
    assert restored['status']=='completed' and restored['completed']==3
    assert c.post('/api/v1/imports/'+jid+'/pause',json={}).status_code==409
    chapters=c.get(f'/api/v1/projects/{pid}/chapters').json()['items']
    assert [ch['number'] for ch in chapters]==[1,2,3,4]


def test_markdown_extension_matches_frontend(studio):
    c,_,_=studio
    r=c.post('/api/v1/imports/preview',files={'file':('作品.markdown','# 第一章\n原文'.encode(),'text/markdown')})
    assert r.status_code==200 and r.json()['chapters'][0]['content']=='原文'
