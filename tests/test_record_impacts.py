from conftest import project,chapter,rev,save,commit


def test_setting_changes_require_impact_confirmation(studio):
    c,_,_=studio; p=project(c); cid=chapter(c,p['id'])
    v=save(c,cid,p['id'],'林舟有一封信。'); commit(c,cid,p['id'],v)
    old=c.post(f'/api/v1/projects/{p["id"]}/records',json={'kind':'rule','title':'信件','content':'林舟知道信件内容','status':'confirmed'}).json()
    derived=c.post(f'/api/v1/projects/{p["id"]}/records',json={'kind':'event','title':'追查','content':'根据信件去旧城','status':'confirmed','dependencies':[old['id']]}).json()
    changed=c.patch('/api/v1/records/'+old['id'],json={'expected_revision':rev(c,p['id']),'content':'林舟尚未看过信件'}).json()
    assert changed['impact']['items'][0]['chapter_id']==cid['id']
    bypass=commit(c,cid,p['id'],v,key='bypass',accepted_memory_ids=[changed['id']])
    assert bypass.status_code==409
    endpoint='/api/v1/records/'+changed['id']+'/approve'
    assert c.post(endpoint,json={'expected_revision':rev(c,p['id'])}).status_code==409
    response=c.post(endpoint,json={'expected_revision':rev(c,p['id']),'impact_acknowledged':True})
    assert response.status_code==200,response.text
    assert c.get('/api/v1/chapters/'+cid['id']).json()['blocked']
    assert derived['id'] not in {x['id'] for x in c.get(f'/api/v1/projects/{p["id"]}/search?q=追查').json()['items']}


def test_withdraw_setting_requires_preview(studio):
    c,_,_=studio; p=project(c); chapter(c,p['id'])
    r=c.post(f'/api/v1/projects/{p["id"]}/records',json={'kind':'rule','title':'规则','content':'魔法有代价','status':'confirmed'}).json()
    endpoint='/api/v1/records/'+r['id']
    assert c.post(endpoint+'/retire',json={'expected_revision':rev(c,p['id']),'reason':'重写世界规则'}).status_code==409
    impact=c.get(endpoint+'/impact').json()
    assert impact['source_record_id']==r['id']
    assert c.post(endpoint+'/retire',json={'expected_revision':rev(c,p['id']),'reason':'重写世界规则','impact_acknowledged':True}).status_code==200
