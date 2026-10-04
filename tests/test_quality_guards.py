import concurrent.futures
import json
import os
from unittest.mock import patch

import httpx
from conftest import project, chapter, provider, wait_run
from test_generation_limits import run_body


def test_future_risks_and_untraceable_criticism_do_not_trigger_rewrite(studio):
    c, _, fixture=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    original=fixture.__class__.__call__
    def critics(self,request):
        response=original(self,request); data=response.json()
        prompt=json.loads(request.content)['messages'][-1]['content']
        if '"title": "ReviewOutput"' in prompt:
            output={'issues':[{'severity':'critical','category':'future_magic','description':'后文可能误用玉佩','basis':'future_risk','quote':'林舟拾起玉佩。'},
                              {'severity':'critical','category':'made_up','description':'这句话不在正文','basis':'observed_conflict','quote':'林舟见到了已死亡的父亲。'}],'summary':'审稿风险'}
            data['choices'][0]['message']['content']=json.dumps(output,ensure_ascii=False)
        return httpx.Response(200,json=data)
    with patch.object(fixture.__class__,'__call__',critics):
        r=c.post('/api/v1/projects/'+p['id']+'/runs',json=run_body(ch,model,auto_approve_plan=True)).json()
        result=wait_run(c,r['id'],['awaiting_review','failed','paused'])
    assert result['status']=='awaiting_review',result
    assert not result['artifacts'].get('revision_round')
    assert all(i['severity']=='warning' for v in result['artifacts']['reviews'] for i in v['issues'])


def test_polish_cannot_leave_new_critical_problem_in_candidate(studio):
    c, _, fixture=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    original=fixture.__class__.__call__
    def changing_style(self,request):
        response=original(self,request); data=response.json()
        prompt=json.loads(request.content)['messages'][-1]['content']
        if '只修订语言' in prompt:
            output={'content':'玉佩复活了死者。','plan_changed':False}
            data['choices'][0]['message']['content']=json.dumps(output,ensure_ascii=False)
        elif '"title": "ReviewOutput"' in prompt and '玉佩复活了死者' in prompt:
            output={'issues':[{'severity':'critical','category':'plot','description':'润色改变了事件','basis':'observed_conflict','quote':'玉佩复活了死者。'}],'summary':'重大变化'}
            data['choices'][0]['message']['content']=json.dumps(output,ensure_ascii=False)
        return httpx.Response(200,json=data)
    with patch.object(fixture.__class__,'__call__',changing_style):
        r=c.post('/api/v1/projects/'+p['id']+'/runs',json=run_body(ch,model,auto_approve_plan=True)).json()
        result=wait_run(c,r['id'],['awaiting_review','failed','paused'])
    assert result['status']=='awaiting_review',result
    assert result['artifacts']['style_rejected']
    assert '复活' not in result['artifacts']['draft']
    assert result['artifacts']['rejected_style_reviews'][0]['issues'][0]['severity']=='critical'


def test_multiscene_word_count_is_distributed(studio):
    c, _, fixture=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    original=fixture.__class__.__call__
    def scenes(self,request):
        response=original(self,request); data=response.json()
        prompt=json.loads(request.content)['messages'][-1]['content']
        if '"title": "PlansOutput"' in prompt:
            output=json.loads(data['choices'][0]['message']['content'])
            output['plans'][0]['scenes']*=2
            data['choices'][0]['message']['content']=json.dumps(output,ensure_ascii=False)
        return httpx.Response(200,json=data)
    with patch.object(fixture.__class__,'__call__',scenes):
        r=c.post('/api/v1/projects/'+p['id']+'/runs',json=run_body(ch,model,task='写约1000汉字的第一章',auto_approve_plan=True)).json()
        result=wait_run(c,r['id'],['awaiting_review','failed','paused'])
    assert result['status']=='awaiting_review',result
    scene_prompts=[json.loads(q.content)['messages'][-1]['content'] for q in fixture.requests if '当前场景是全章' in q.content.decode('utf-8')]
    assert len(scene_prompts)==2 and all('篇幅约500汉字' in t for t in scene_prompts)


def test_parallel_independent_migrations_and_parent_liveness(tmp_path):
    from easynovel.database import Database
    from easynovel.__main__ import parent_alive
    databases=[Database(tmp_path/str(n)/'test.sqlite3') for n in range(3)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda db:db.initialize(),databases))
    from sqlalchemy import text
    for db in databases:
        with db.read() as s: assert s.execute(text('SELECT version_num FROM alembic_version')).scalar()=='0003'
        db.engine.dispose()
    assert parent_alive(os.getpid())
    assert not parent_alive(0x7fffffff)


def test_overlong_draft_is_compressed_once_then_reviewed(studio):
    c,_,fixture=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    original=fixture.__class__.__call__
    def long_draft(self,request):
        response=original(self,request); data=response.json()
        prompt=json.loads(request.content)['messages'][-1]['content']
        if '当前场景是全章' in prompt:
            data['choices'][0]['message']['content']=json.dumps({'content':'林舟拾起玉佩。'+'他认出旧时的名字。'*30,'plan_changed':False},ensure_ascii=False)
        return httpx.Response(200,json=data)
    with patch.object(fixture.__class__,'__call__',long_draft):
        r=c.post('/api/v1/projects/'+p['id']+'/runs',json=run_body(ch,model,task='写约100字的第一章',auto_approve_plan=True)).json()
        result=wait_run(c,r['id'],['awaiting_review','failed','paused'])
    assert result['status']=='awaiting_review',result
    assert len(result['artifacts']['before_length'])>150
    assert len(result['artifacts']['draft'])<100
    calls=c.get('/api/v1/runs/'+r['id']+'/calls').json()
    assert sum(call['call_key'].startswith('length:') for call in calls)==1
    assert result['artifacts']['reviews']
