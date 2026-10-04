"""Explicit, bounded real-model smoke test. Never loads or prints .env files."""
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from easynovel.app import create_app
from easynovel.config import Settings


def main():
    key=os.environ.get('DEEPSEEK_API_KEY')
    if not key: raise SystemExit('DEEPSEEK_API_KEY not present')
    folder=Path('artifacts/live-smoke')
    app=create_app(Settings(data_dir=folder/'data',token='isolated-live-test',test_mode=True,legacy_path=folder/'absent.db'))
    with TestClient(app,headers={'Authorization':'Bearer isolated-live-test'}) as client:
        def post(path,body):
            r=client.post('/api/v1'+path,json=body)
            if r.status_code!=200: raise RuntimeError(f'{path}: HTTP {r.status_code}: {r.text[:300]}')
            return r.json()
        def wait(identity,expected):
            last=None
            for _ in range(600):
                r=client.get('/api/v1/runs/'+identity).json()
                if (r['node'],r['status'])!=last:
                    print(json.dumps({'node':r['node'],'status':r['status'],'usage':r['usage']},ensure_ascii=False),flush=True)
                    last=(r['node'],r['status'])
                if r['status']==expected or r['status'] in ('failed','paused','stale','cancelled'): return r
                time.sleep(1)
            raise RuntimeError('live smoke timeout')
        if '--resume' in sys.argv:
            rid=sys.argv[sys.argv.index('--resume')+1]
            existing=client.get('/api/v1/runs/'+rid).json()
            model=next(m for m in client.get('/api/v1/providers').json() if m['id']==existing['request']['provider_id'])
            app.state.credentials.set(model['id'],key)
            p=client.get('/api/v1/projects/'+existing['project_id']).json()
            ch=client.get('/api/v1/chapters/'+existing['chapter_id']).json()
            r=existing
            if existing['status'] in ('paused','failed'): post('/runs/'+rid+'/resume',{'role_limits':{'memory':4096}})
        else:
            return prepare_new(client,post,app,key,wait,folder)
        finish(client,post,wait,folder,p,ch,r)


def prepare_new(client,post,app,key,wait,folder):
        model=post('/providers',{'name':'DeepSeek Flash 实测','base_url':'https://api.deepseek.com/v1','model':'deepseek-flash','context_limit':64000,'max_output':4096,'extra_body':{'thinking':{'type':'disabled'}}})
        app.state.credentials.set(model['id'],key)
        profile=post('/profiles',{'name':'有界端到端实测','max_revisions':0,'roles':{'architect':{'max_output':512},'planner':{'max_output':2048},'writer':{'max_output':4096},'continuity':{'max_output':2048},'editor':{'max_output':2048},'stylist':{'max_output':4096},'memory':{'max_output':2048}}})
        p=post('/projects',{'title':'夜渡旧城 · 实测','mode':'literary','genre':'悬疑','description':'测试人物认知与玉佩伏笔，不涉及真实用户作品'})
        ch=post(f'/projects/{p["id"]}/chapters',{'title':'雨夜的渡口','story_time':3})
        for record in [
            {'kind':'character','title':'林舟','content':'落魄的修表匠。找失踪父亲，怕自己的判断伤害朋友。话少，习惯通过细节观察。','entity_ids':['林舟'],'data':{'aliases':['小舟'],'goal':'寻找父亲','fear':'误伤朋友','voice':'克制、具体'}},
            {'kind':'character','title':'苏雨','content':'渡船女船工，知道林舟父亲留下的信件但没有告诉林舟。','entity_ids':['苏雨']},
            {'kind':'knowledge','title':'苏雨知道信件','content':'苏雨亲眼看过父亲留下的信件，林舟还没有看过，也不知道信件存在。','data':{'character_id':'苏雨','acquisition':'亲眼阅读'}},
            {'kind':'foreshadow','title':'十八年前的玉佩','content':'林舟保留的裂纹玉佩来自父亲，纹样可能关联旧城渡口。只呈现线索，不直接揭示父亲下落。','entity_ids':['林舟'],'data':{'status':'open','payoff_start':1}},
            {'kind':'rule','title':'人物认知限制','content':'林舟不知道信件存在。不能用旁白让他突然知道。人物关系变化必须有行动诱因。'}]:
            post(f'/projects/{p["id"]}/records',{**record,'status':'confirmed'})
        r=post(f'/projects/{p["id"]}/runs',{'chapter_id':ch['id'],'task':'写约800字中文悬疑小说开篇。雨夜渡口，林舟想借船寻找旧城线索，苏雨犹豫。安排两个场景以内，玉佩刻痕让她改变决定，但不揭示信件。让人物各有代价，避免模板感叹与强行悬念。','pov':'林舟','provider_id':model['id'],'profile_id':profile['id'],'token_budget':100000})
        finish(client,post,wait,folder,p,ch,r)


def finish(client,post,wait,folder,p,ch,r):
        if r['node'] in ('context','architect','planner','approve_plan'):
            stage=wait(r['id'],'awaiting_plan')
            if stage['status']!='awaiting_plan': raise RuntimeError(stage.get('error') or 'plan not ready')
            post(f'/runs/{r["id"]}/approve-plan',{'plan_index':0})
        stage=wait(r['id'],'awaiting_review')
        if stage['status']!='awaiting_review': raise RuntimeError(stage.get('error') or 'review not ready')
        accepted=[i for i,item in enumerate(stage['artifacts']['memory_delta']) if item['source_type']!='inference']
        current=client.get('/api/v1/projects/'+p['id']).json()
        post(f'/runs/{r["id"]}/approve',{'expected_revision':current['revision'],'idempotency_key':'live-'+r['id'],'accepted_memory_indices':accepted,'override_reason':'隔离端到端测试确认；问题保留在测试报告中，不代表文学质量验收'})
        done=wait(r['id'],'completed')
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'chapter.md').write_text(stage['artifacts']['draft'],encoding='utf-8')
        report={'model':'deepseek-flash','project_id':p['id'],'run_id':r['id'],'status':done['status'],'usage':done['usage'],'reviews':stage['artifacts']['reviews'],'accepted_memory_count':len(accepted),'candidate_memory_count':len(stage['artifacts']['memory_delta']),'budget_tokens':100000}
        (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False),flush=True)
        if done['status']!='completed': raise RuntimeError(done.get('error') or 'commit failed')


if __name__=='__main__': main()
