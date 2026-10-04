"""Bounded, isolated paid workflow exercise; never reads .env or the user's novel DB."""
import argparse
import concurrent.futures
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from easynovel.app import create_app
from easynovel.config import Settings

CASES=[
    {'id':'mystery','title':'旧钟停在四点十七分','mode':'literary','genre':'悬疑',
     'bible':'修钟师沈默的父亲失踪三年。刑警顾岚曾接受父亲帮助。父亲的铜钥匙有一道斜槽，沈默一直随身保管。沈默不知道父亲留下过信件；顾岚也没读过信。旧钟铺停业多年，没有通电。叙述限于沈默可观察的信息，不能用巧合或万能技术解谜。',
     'tasks':['写第一章：顾岚带沈默进入被封的旧钟铺，柜台下出现一枚新鲜指纹，铜钥匙只能开启一个小抽屉。揭示父亲曾保护陌生孩子的线索，不揭示失踪答案。约1000汉字，一到两个场景。',
              '写第二章：紧接第一章。沈默依据上一章真实出现的证据寻找孩子，顾岚面临是否上报线索的职业代价。回扣钥匙的斜槽，得出一个可验证的小结论，但父亲去向仍未知。约1000汉字，一到两个场景。']},
    {'id':'fantasy','title':'借火的人','mode':'serial','genre':'奇幻',
     'bible':'见习炉匠阿榆靠修灯维生。她的导师莫川左手残疾，欠城卫债务。魔法规则：每借一次灵火会失去一个最近二十四小时的真实记忆，失去内容不能靠施术者意志指定；灵火不能复活死人，也不能凭空创造食物。阿榆的母亲留给她一个生锈的铜铃，铜铃并无已确认魔力。阿榆珍惜和妹妹阿杏的约定。',
     'tasks':['写第一章：寒潮来临，灯炉损坏。阿榆必须在交不起罚金与借灵火之间选择，第一次付出失去记忆的代价。妹妹阿杏参与冲突，铜铃自然出现。约1000汉字，一到两个场景。不要轻易解释铜铃意义。',
              '写第二章：延续第一章的实际代价和结局。阿榆尝试用纸笔补救失去的记忆，却发现记录不能代替情感和信任。莫川的债务迫使她做一项有风险的交易；兑现一个近期承诺而非继续堆秘密。约1000汉字，一到两个场景。']},
    {'id':'daily','title':'最后一班公交','mode':'literary','genre':'都市成长',
     'bible':'许宁是准备离职的社区文员，擅长做表格而不善表达感情。朋友陆遥开修车店，不会说漂亮话。许宁母亲每天发饭菜照片但从不问他是否开心。许宁必须在周五前决定是否接受外地职位；当前周三。故事不使用超自然力量，人物改变需要行动和代价，不强制每章悬念。',
     'tasks':['写第一章：许宁错过末班公交，与忙着修车的陆遥争执。城市改造通知意味着修车店月底要搬走。以一个具体的帮忙行动显示他们关系中的不对等，让母亲饭菜照片自然出现。约1000汉字，一到两个场景，克制具体的语言。',
              '写第二章：第二天周四，许宁试图帮助陆遥搬店，但外地职位要求当天答复，和周五原期限形成真实选择。回扣母亲照片，通过有潜台词的电话和行动推进人物，不强行和解。延续第一章实际事件，约1000汉字，一到两个场景。']},
]

def exercise(case,folder,key,continue_existing=False):
    data=folder/case['id']; report={'case':case['id'],'title':case['title'],'chapters':[]}
    app=create_app(Settings(data_dir=data/'data',token='isolated-acceptance',test_mode=True,legacy_path=data/'absent.db'))
    with TestClient(app,headers={'Authorization':'Bearer isolated-acceptance'}) as c:
        def post(path,body):
            response=c.post('/api/v1'+path,json=body)
            if response.status_code!=200: raise RuntimeError(f'{path}: HTTP {response.status_code}: {response.text[:250]}')
            return response.json()
        prior=json.loads((data/'report.json').read_text(encoding='utf-8')) if continue_existing and (data/'report.json').exists() else None
        existing_projects=c.get('/api/v1/projects').json() if prior else []
        if existing_projects:
            p=existing_projects[0]
            old_run=c.get('/api/v1/runs/'+prior['chapters'][0]['run_id']).json()
            model=next(m for m in c.get('/api/v1/providers').json() if m['id']==old_run['request']['provider_id'])
            profile={'id':old_run['request']['profile_id']}
        else:
            model=post('/providers',{'name':'验收 DeepSeek','base_url':'https://api.deepseek.com/v1','model':'deepseek-flash','context_limit':64000,'max_output':8192,'extra_body':{'thinking':{'type':'disabled'}}})
        app.state.credentials.set(model['id'],key)
        if not existing_projects:
            profile=post('/profiles',{'name':'完整质量流程','max_revisions':2,'roles':{
            'architect':{'max_output':4096,'prompt':'给出简洁架构建议，控制在400汉字以内。'},
            'planner':{'max_output':8192,'prompt':'单章最多两个场景；整体字数目标是全章目标，不是每场景各写一章。'},
            'writer':{'max_output':8192,'prompt':'尊重总篇幅，场景正文不要重复复述上一个场景。'},
            'continuity':{'max_output':4096,'prompt':'最多指出六项确有证据的问题，不为凑数臆造矛盾。'},
            'editor':{'max_output':4096,'prompt':'最多指出六项实质问题，区分审美建议与逻辑错误。'},
            'stylist':{'max_output':8192},'memory':{'max_output':8192}}})
            p=post('/projects',{'title':case['title'],'mode':case['mode'],'genre':case['genre']})
            post('/projects/'+p['id']+'/records',{'kind':'directive','title':'验收创作约束','content':case['bible'],'status':'confirmed','data':{'hard':True,'scope':'book'}})
        for number,task in enumerate(case['tasks'],1):
            old=next((x for x in (prior or {}).get('chapters',[]) if x['number']==number),None)
            if old and old.get('commit_status')=='completed':
                report['chapters'].append(old)
                continue
            if old:
                run=c.get('/api/v1/runs/'+old['run_id']).json()
                ch=c.get('/api/v1/chapters/'+run['chapter_id']).json()
                if run['status']=='awaiting_review': post('/runs/'+run['id']+'/edit',{'draft':run['artifacts']['draft']})
                elif run['status'] in ('paused','failed'): post('/runs/'+run['id']+'/resume',{})
            else:
                ch=post('/projects/'+p['id']+'/chapters',{'title':f'第{number}章','number':number})
                run=post('/projects/'+p['id']+'/runs',{'chapter_id':ch['id'],'task':task,'provider_id':model['id'],'profile_id':profile['id'],'token_budget':200000,'auto_approve_plan':True})
            last=None; resumed=False
            for _ in range(1200):
                current=c.get('/api/v1/runs/'+run['id']).json()
                stage=(current['node'],current['status'])
                if stage!=last:
                    print(json.dumps({'case':case['id'],'chapter':number,'node':stage[0],'status':stage[1],'usage':current['usage']},ensure_ascii=False),flush=True); last=stage
                if current['status']=='paused' and current['artifacts'].get('output_limit_info') and not resumed:
                    info=current['artifacts']['output_limit_info']; limit=min(16384,info['context_limit']//2)
                    post('/runs/'+run['id']+'/resume',{'role_limits':{info['role']:limit},'provider_output_limits':{info['provider_id']:limit}}); resumed=True
                elif current['status'] in ('awaiting_review','failed','paused','stale','cancelled','awaiting_plan'): break
                time.sleep(1)
            data.mkdir(parents=True,exist_ok=True)
            draft=current['artifacts'].get('draft','')
            (data/f'chapter-{number}.md').write_text(draft,encoding='utf-8')
            (data/f'run-{number}.json').write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
            item={'number':number,'run_id':run['id'],'status':current['status'],'characters':len(draft),'usage':current['usage'],'reviews':current['artifacts'].get('reviews',[]),'revision_rounds':current['artifacts'].get('revision_round',0),'error':current.get('error')}
            report['chapters'].append(item)
            if current['status']!='awaiting_review': break
            critical=[i for review in item['reviews'] for i in review['issues'] if i['severity']=='critical']
            if critical:
                item['quality_gate']='critical_issues_remain'; break
            selected=[i for i,m in enumerate(current['artifacts'].get('memory_delta',[])) if m['source_type']!='inference']
            revision=c.get('/api/v1/projects/'+p['id']).json()['revision']
            post('/runs/'+run['id']+'/approve',{'expected_revision':revision,'idempotency_key':'acceptance-'+run['id'],'accepted_memory_indices':selected})
            for _ in range(100):
                done=c.get('/api/v1/runs/'+run['id']).json()
                if done['status'] in ('completed','failed','stale'): break
                time.sleep(.1)
            item['commit_status']=done['status']; item['accepted_memory']=len(selected)
            if done['status']!='completed': break
    (data/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--folder',default='artifacts/acceptance-novels'); parser.add_argument('--continue',dest='continue_existing',action='store_true'); args=parser.parse_args()
    key=os.environ.get('DEEPSEEK_API_KEY')
    if not key: raise SystemExit('DEEPSEEK_API_KEY is not available; no .env file is read.')
    folder=Path(args.folder); folder.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        reports=list(pool.map(lambda case:exercise(case,folder,key,args.continue_existing),CASES))
    (folder/'report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'completed_chapters':sum(sum(c.get('commit_status')=='completed' for c in r['chapters']) for r in reports),'report':str(folder/'report.json')},ensure_ascii=False),flush=True)
    if any(len(r['chapters'])!=2 or any(c.get('commit_status')!='completed' for c in r['chapters']) for r in reports): raise SystemExit(1)

if __name__=='__main__': main()
