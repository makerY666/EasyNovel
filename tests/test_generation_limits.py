import json

from conftest import project, chapter, provider, wait_run, save


def run_body(ch, model, **extra):
    return {'chapter_id':ch['id'],'task':'写第一章，林舟发现玉佩。','provider_id':model['id'],'token_budget':1000000,**extra}


def test_architecture_uses_configured_limit_not_hardcoded_1024(studio):
    c, _, fixture=studio; p=project(c); ch=chapter(c,p['id'])
    model=c.post('/api/v1/providers',json={'name':'长输出模型','base_url':'https://fixture.invalid/v1','model':'test','max_output':8192}).json()
    r=c.post(f'/api/v1/projects/{p["id"]}/runs',json=run_body(ch,model)).json()
    assert wait_run(c,r['id'],['awaiting_plan','paused','failed'])['status']=='awaiting_plan'
    assert json.loads(fixture.requests[0].content)['max_tokens']==8192


def test_quick_write_stops_for_author_review_without_committing(studio):
    c, _, _=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    r=c.post(f'/api/v1/projects/{p["id"]}/runs',json=run_body(ch,model,auto_approve_plan=True)).json()
    result=wait_run(c,r['id'],['awaiting_review','paused','failed'])
    assert result['status']=='awaiting_review',result
    assert '林舟拾起玉佩' in result['artifacts']['draft']
    assert result['artifacts']['plan_approval']['author_requested'] is True
    assert result['artifacts']['version_id']
    assert not c.get(f'/api/v1/projects/{p["id"]}/records').json()
    assert c.get(f'/api/v1/chapters/{ch["id"]}').json()['confirmed_version_id'] is None


def test_truncated_result_remains_paused_until_output_limit_changes(studio):
    c, _, fixture=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    original=fixture.__class__.__call__
    def capped(self,request):
        response=original(self,request)
        body=json.loads(request.content)
        data=response.json()
        if body['max_tokens']<=1024:
            data['choices'][0]['finish_reason']='length'
            data['usage']['completion_tokens']=1024
        else: data['choices'][0]['finish_reason']='stop'
        import httpx
        return httpx.Response(200,json=data)
    from unittest.mock import patch
    with patch.object(fixture.__class__,'__call__',capped):
        r=c.post(f'/api/v1/projects/{p["id"]}/runs',json=run_body(ch,model)).json()
        paused=wait_run(c,r['id'],['paused','failed'])
        assert paused['status']=='paused',paused
        assert '不是任务总额度' in paused['error']
        info=paused['artifacts']['output_limit_info']
        assert info['maximum']==1024 and info['role']=='architect'
        calls=c.get(f'/api/v1/runs/{r["id"]}/calls').json()
        assert calls[0]['usage']['finish_reason']=='length' and calls[0]['result']
        before=len(fixture.requests)
        assert c.post(f'/api/v1/runs/{r["id"]}/resume',json={}).status_code==200
        paused=wait_run(c,r['id'],['paused','failed'])
        assert paused['status']=='paused'
        assert len(fixture.requests)==before
        assert c.post(f'/api/v1/runs/{r["id"]}/resume',json={'role_limits':{'architect':8192},'provider_output_limits':{model['id']:8192}}).status_code==200
        result=wait_run(c,r['id'],['awaiting_plan','paused','failed'])
        assert result['status']=='awaiting_plan',result
        assert json.loads(fixture.requests[before].content)['max_tokens']==8192
        assert result['usage']['output_tokens']>=1024


def test_resume_output_limit_validation_is_atomic(studio):
    c, _, _=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    r=c.post(f'/api/v1/projects/{p["id"]}/runs',json=run_body(ch,model,token_budget=100)).json()
    wait_run(c,r['id'],['paused'])
    response=c.post(f'/api/v1/runs/{r["id"]}/resume',json={'token_budget':1000000,'provider_output_limits':{model['id']:100000}})
    assert response.status_code==422
    unchanged=c.get(f'/api/v1/runs/{r["id"]}').json()
    assert unchanged['request']['token_budget']==100 and unchanged['status']=='paused'


def test_generated_prose_preserves_locked_paragraph_identity(studio):
    c, _, fixture=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    before=save(c,ch,p['id'],'林舟拾起玉佩。',paragraphs=[{'id':'locked-opening','text':'林舟拾起玉佩。','locked':True}])
    r=c.post(f'/api/v1/projects/{p["id"]}/runs',json=run_body(ch,model,auto_approve_plan=True)).json()
    result=wait_run(c,r['id'],['awaiting_review','paused','failed','stale'])
    assert result['status']=='awaiting_review',result
    detail=c.get('/api/v1/chapters/'+ch['id']).json()
    assert detail['draft']['paragraphs'][0]==before['paragraphs'][0]
    writer_requests=[json.loads(q.content) for q in fixture.requests if 'DraftOutput' in q.content.decode('utf-8')]
    assert all('locked-opening' in q['messages'][-1]['content'] for q in writer_requests)


def test_lock_violation_preserves_candidate_without_overwriting_author(studio):
    c, _, _=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    before=save(c,ch,p['id'],'锁定对白：我不会离开。',paragraphs=[{'id':'locked-dialogue','text':'锁定对白：我不会离开。','locked':True}])
    r=c.post(f'/api/v1/projects/{p["id"]}/runs',json=run_body(ch,model,auto_approve_plan=True)).json()
    result=wait_run(c,r['id'],['awaiting_review','failed','stale'])
    assert result['status']=='stale' and result['artifacts']['draft']
    assert c.get('/api/v1/chapters/'+ch['id']).json()['draft_version_id']==before['id']
