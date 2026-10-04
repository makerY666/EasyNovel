"""Exercise explicit author feedback, canon impact and repair on isolated generated novels."""
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

NOTES={
 'mystery':[
  '保留旧钟铺、孩子旧衣服与铜钥匙线索。沈默持有钥匙三年，不是失踪父亲在这三年持有钥匙。修钟师不能凭灰上指纹间距断定男性或精确断定两三天，改为灰被碰过的近期痕迹，保持推断的不确定性。缝针方向不证明左撇子身份，改为他认得父亲补衣服的一种具体习惯但仍只是推测。以动作展现他对父亲的认识发生动摇，不重复末尾比喻。约1000汉字，保留两场景的核心因果。',
  '延续已修订第一章，整章严格限于沈默可观察或合理推断的信息，不能切入顾岚内心或展示沈默看不到的手机打字。删除“第一章里”及任何章外编号回顾。钥匙是沈默持有三年，父亲为何留钥匙只能推断，不能凭锁型确定铸造用途或知道父亲全部意图。避免重复验证上一章已经验证的同一结论；推进一项新线索或可验证小结论。顾岚是否上报的职业代价通过她可被沈默听见的话或行动表现，别擅自揭示父亲去向。约1000汉字。'],
 'fantasy':[
  '保留寒潮、灯炉损坏、阿榆为妹妹借火以及付出记忆代价。代价只抽走最近24小时内的一次具体真实记忆：昨日下午和阿杏聊铜铃的对话；不会抹掉多年以前母亲留下铜铃的童年记忆，也不会抹掉施法后新发生的事。清楚按先后写施法前记得、施法后忘记，不反复泛写“丢了东西”。铜铃没有被确认魔力，普通巧合不能写成已知魔法。罚金八十仍要解决，烧罚单不能免债。约1000汉字，克制具体。',
  '延续修订第一章。阿榆无法准确从自身记忆写出已经被灵火抹去的昨日下午铜铃对话；纸上有关丢失内容必须来自阿杏重新告诉她，并区分“别人告诉我”与“我亲历记得”。阿杏记得不等于阿榆恢复体验，借记录补救带来关系的真实变化。没有第二次施法，不能把今早或出门前的新记忆也抹去。若阿杏说今天重复说过龙灯，阿榆没听进去必须明确是压力下分心，不能归因昨晚灵火；不要用反复误会推动。莫川有另一笔债，不把他旧债和阿榆罚金混为同一笔；保留交易的风险和实际陪妹妹看灯的兑现。约1000汉字。'],
 'daily':[
  '保留修车店月底腾退、许宁整理单据、陆遥送坐垫与母亲饭菜照片。开头明确许宁错过末班公交，随后去修车店，与陆遥的争执要自然。单据已放入抽屉后，不能又在工具箱上对齐同三摞纸，可写他手悬着想整理但收回。谈到母亲饭菜时先有照片或合适触发，不凭空跳话题。物品放到椅子、抽屉或袋子后位置要连贯。约1000汉字，克制对白，不强制悬念。',
  '延续修订第一章。今天周四，外地职位把原周五期限提前到今天下班前。搬箱子、留箱子与明早装车的时间和位置说清，坐垫昨晚已拿出放椅子上不能又凭空留在袋里。去掉重复两次问同一个明早装车时间的对白。不要让场景只反复亮手机、删消息和拖延：在今天下班前给岗位方一个具体答复或有代价的要求，使人物有实际行动，但不强行与母亲或陆遥和解。母亲照片保持潜台词，不解释所有感情。约1000汉字。']}

def exercise(case,root,key):
    data=root/case; original=json.loads((data/'report.json').read_text(encoding='utf-8'))
    output=data/'reader-revision'; output.mkdir(exist_ok=True)
    app=create_app(Settings(data_dir=data/'data',token='reader-test',test_mode=True,legacy_path=data/'absent.db'))
    previous=json.loads((output/'report.json').read_text(encoding='utf-8')) if (output/'report.json').exists() else []
    report=[]; impacts=[]
    with TestClient(app,headers={'Authorization':'Bearer reader-test'}) as c:
        def post(path,body):
            response=c.post('/api/v1'+path,json=body)
            if response.status_code!=200: raise RuntimeError(f'{case} {path}: {response.status_code} {response.text[:200]}')
            return response.json()
        for model in c.get('/api/v1/providers').json(): app.state.credentials.set(model['id'],key)
        for number,instruction in enumerate(NOTES[case],1):
            earlier=next((item for item in previous if item['number']==number),None)
            if earlier and earlier.get('commit_status')=='completed':
                report.append(earlier)
                saved=c.get('/api/v1/runs/'+earlier['run_id']).json()
                pid=saved['project_id']
                impact=saved['artifacts'].get('commit',{}).get('impact')
                if impact and impact['items']: impacts.append(impact)
                continue
            parent=next(x for x in original['chapters'] if x['number']==number)
            if earlier:
                candidate=c.get('/api/v1/runs/'+earlier['run_id']).json()
                if candidate['status']=='awaiting_review':
                    parent=earlier
                    critical=[i for review in candidate['artifacts'].get('reviews',[]) for i in review['issues'] if i['severity']=='critical']
                    instruction+='\n逐项解决已发现的正文关键问题：'+json.dumps(critical,ensure_ascii=False)
                for prefix,suffix in [('run','json'),('chapter','md')]:
                    path=output/f'{prefix}-{number}.{suffix}'
                    if path.exists(): path.replace(output/f'{prefix}-{number}-before-retry.{suffix}')
            source=c.get('/api/v1/runs/'+parent['run_id']).json(); pid=source['project_id']
            revision=c.get('/api/v1/projects/'+pid).json()['revision']
            run=post('/runs/'+source['id']+'/revise',{'instruction':instruction,'expected_revision':revision})
            last=None
            for _ in range(600):
                result=c.get('/api/v1/runs/'+run['id']).json(); stage=(result['node'],result['status'])
                if stage!=last: print(json.dumps({'case':case,'chapter':number,'node':stage[0],'status':stage[1],'usage':result['usage']},ensure_ascii=False),flush=True); last=stage
                if result['status'] in ('awaiting_review','awaiting_plan','failed','paused','stale'): break
                time.sleep(1)
            (output/f'chapter-{number}.md').write_text(result['artifacts'].get('draft',''),encoding='utf-8')
            (output/f'run-{number}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            item={'number':number,'run_id':run['id'],'status':result['status'],'characters':len(result['artifacts'].get('draft','')),'usage':result['usage'],'reviews':result['artifacts'].get('reviews',[]),'error':result.get('error')}; report.append(item)
            (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            critical=[i for v in item['reviews'] for i in v['issues'] if i['severity']=='critical']
            if result['status']!='awaiting_review' or critical: break
            selected=[i for i,m in enumerate(result['artifacts'].get('memory_delta',[])) if m['source_type']!='inference']
            post('/runs/'+run['id']+'/approve',{'expected_revision':result['input_revision'],'idempotency_key':'reader-'+run['id'],'accepted_memory_indices':selected})
            for _ in range(100):
                done=c.get('/api/v1/runs/'+run['id']).json()
                if done['status'] in ('completed','failed','stale'): break
                time.sleep(.1)
            item['commit_status']=done['status']
            impact=done['artifacts'].get('commit',{}).get('impact')
            if impact and impact['items']: impacts.append(impact)
            if done['status']!='completed': break
        if len(report)==2 and all(i.get('commit_status')=='completed' for i in report):
            for impact in impacts:
                post('/impact/'+impact['id']+'/resolve',{'chapter_ids':[i['chapter_id'] for i in impact['items']],'expected_revision':c.get('/api/v1/projects/'+pid).json()['revision'],'reason':'隔离验收：第二章已经依据修订第一章重写、审核并确认，核查记忆时间与物品衔接。'})
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    key=os.environ.get('DEEPSEEK_API_KEY')
    if not key: raise SystemExit('DEEPSEEK_API_KEY unavailable')
    root=Path(sys.argv[1])
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: results=list(pool.map(lambda case:exercise(case,root,key),NOTES))
    print(json.dumps({'completed_revisions':sum(sum(i.get('commit_status')=='completed' for i in rows) for rows in results)},ensure_ascii=False),flush=True)
    if any(len(rows)!=2 or any(i.get('commit_status')!='completed' for i in rows) for rows in results): raise SystemExit(1)
