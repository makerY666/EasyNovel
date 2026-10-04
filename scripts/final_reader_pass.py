"""One bounded author revision pass on isolated paid acceptance data, with preserved originals."""
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
from reader_revision import NOTES

EXTRA={
 'daily':[
  '保留目前大部分正文，只删重复尾段意象，长度控制1000至1200字。坐垫共两个，回家都从袋子里拿出放椅子上，袋子是空的。单据全留在修车店抽屉。',
  '必须删除末段“昨晚从店里带回来的单据”：单据全在店内抽屉。只问一次装车时间，工具箱尚在店里、待装明早车，今天不是已装同一辆车。清楚写陆遥把一箱工具暂放许宁楼下，请他明早六点五十搬来，许宁实际搬回；不能空口说箱子在而不交接。职位方收到许宁当天下班前明确请求：愿意接受，但需延后一天报到；对方明确此请求造成候选排序风险。他保留承担风险的决定，不在家反复删同一消息。坐垫昨晚已经放椅子上，第二章店里不要再出现相同灰蓝旧坐垫。'],
 'mystery':[
  '无法凭模糊灰痕排除父亲！把“这不是父亲的手”“不是他”改成“看不清，不能判断是谁”，顾岚强调等待现场勘验。失踪父亲有手指疤只能引出疑问，不能当排除结论。孩子旧衣上的习惯针脚只是疑似父亲参与的线索，不是确认保护事实。紧贴沈默视角，1000至1200字。',
  '本章从出店后开始，不要重新复述或测量一整段钥匙的锁型。“沈默自己随身保管钥匙三年”，不是父亲过去三年持有。父亲留钥匙意图未知，更不能凭钥匙浅孔确定父亲精确算好用途。推进一个新线索：顾岚告诉沈默纸片上只有1998与“送去北站”，他记起童年时北站已停客运，两人决定核实当年的货运登记（不要直接查到答案）。职业代价通过顾岚说现场物证需登记但怕惊动举报人表现，不能让她无解释藏证，不写她手机打字和内心。1000至1200字。'],
 'fantasy':[
  '施法前的真实待失记忆发生于今天下午：阿杏在门槛擦铃说“妈说它镇邪”，阿榆笑她；正文开头呈现这段回忆。今夜再谈铜铃不要重复同一对话。失去的只有这一次下午的对话，不是母亲当年交铃的童年经历。施法后记得母亲留下铃但忘记下午自己笑妹妹的体验；明白最近24小时内一段记忆作为代价，不能丢掉施法后新记忆。莫川不在现场，阿榆也不能准确指定代价。罚金还有57缺口：结尾她保留缴款凭条，不烧掉以为免债，准备明早向城卫申请一天缓期。1000至1200字。',
  '开头夜里不要写出失去对话的具体内容；只写“下午擦铃的事，等阿杏明早告诉我”，目前无法知道自己笑了什么。第二天阿杏亲口重讲昨天下午的镇邪话和姐姐笑她，阿榆才写“阿杏说的，不是我记得的”。多年以前母亲交铃的童年记忆仍在，不把失去的一次昨日下午对话扩成失去童年。阿榆去铺子之前阿杏讲龙灯时她还没见禁制炉，不能以思考尚未接手的禁制纹分心；改为担心自己的57枚缺口而分心。师傅债务是240而不是同样80；交易抵120，明确“日落前陪妹妹看灯，散场前修好送到望月桥”，中间人接受这个时间。灯会发生于傍晚不是清晨，清楚切换一天时间。阿杏在灯会前汇合，不突然等待很久。1000至1200字。']}

def exercise(case,root,key):
    folder=root/case; older=json.loads((folder/'reader-revision/report.json').read_text(encoding='utf-8'))
    original=json.loads((folder/'report.json').read_text(encoding='utf-8'))['chapters']
    output=folder/'author-final'; output.mkdir(exist_ok=True)
    app=create_app(Settings(data_dir=folder/'data',token='final-pass',test_mode=True,legacy_path=folder/'absent.db'))
    results=[]
    with TestClient(app,headers={'Authorization':'Bearer final-pass'}) as c:
        def post(path,body):
            response=c.post('/api/v1'+path,json=body)
            if response.status_code!=200: raise RuntimeError(f'{case}: {path} {response.status_code} {response.text[:200]}')
            return response.json()
        for model in c.get('/api/v1/providers').json(): app.state.credentials.set(model['id'],key)
        # An earlier proposed plan has no saved draft head; cancel it and use its unchanged original prose.
        for row in older:
            run=c.get('/api/v1/runs/'+row['run_id']).json()
            if run['status']=='awaiting_plan': post('/runs/'+run['id']+'/cancel',{})
        for number in (1,2):
            row=next(x for x in older if x['number']==number)
            source=c.get('/api/v1/runs/'+row['run_id']).json()
            if source['status']=='cancelled' and not source['artifacts'].get('version_id'):
                source=c.get('/api/v1/runs/'+next(x for x in original if x['number']==number)['run_id']).json()
            pid=source['project_id']
            instruction=NOTES[case][number-1]+'\n具体逐项修改：'+EXTRA[case][number-1]
            run=post('/runs/'+source['id']+'/revise',{'instruction':instruction,'expected_revision':c.get('/api/v1/projects/'+pid).json()['revision']})
            last=None; confirmations=[]
            for _ in range(1200):
                current=c.get('/api/v1/runs/'+run['id']).json(); stage=(current['node'],current['status'])
                if last!=stage: print(json.dumps({'case':case,'chapter':number,'node':stage[0],'status':stage[1],'usage':current['usage']},ensure_ascii=False),flush=True); last=stage
                if current['status']=='awaiting_plan' and len(confirmations)<2:
                    confirmations.append(current['artifacts'].get('proposed_revision',{}).get('change_reason'))
                    post('/runs/'+run['id']+'/approve-plan',{'accept_change':True})
                elif current['status'] in ('awaiting_review','paused','failed','stale','cancelled'): break
                time.sleep(1)
            draft=current['artifacts'].get('draft','')
            (output/f'chapter-{number}.md').write_text(draft,encoding='utf-8')
            (output/f'run-{number}.json').write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
            item={'number':number,'run_id':current['id'],'status':current['status'],'usage':current['usage'],'characters':len(draft),'confirmed_changes':confirmations,'reviews':current['artifacts'].get('reviews',[]),'error':current.get('error')}; results.append(item)
            if current['status']!='awaiting_review': break
            critical=[issue for review in item['reviews'] for issue in review['issues'] if issue['severity']=='critical']
            if critical: break
            post('/runs/'+run['id']+'/approve',{'expected_revision':current['input_revision'],'idempotency_key':'final-pass-'+run['id'],'accepted_memory_indices':[i for i,v in enumerate(current['artifacts'].get('memory_delta',[])) if v['source_type']!='inference']})
            for _ in range(100):
                done=c.get('/api/v1/runs/'+run['id']).json()
                if done['status'] in ('completed','failed','stale'): break
                time.sleep(.1)
            item['commit_status']=done['status']; item['error']=done.get('error')
            if done['status']!='completed': break
    (output/'report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    return results

if __name__=='__main__':
    key=os.environ.get('DEEPSEEK_API_KEY')
    if not key: raise SystemExit('DEEPSEEK_API_KEY unavailable')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows=list(pool.map(lambda case:exercise(case,Path(sys.argv[1]),key),EXTRA))
    print(json.dumps({'completed_final_chapters':sum(sum(r.get('commit_status')=='completed' for r in items) for items in rows)}),flush=True)
