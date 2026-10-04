"""Apply identified author line edits through version, impact and atomic commit APIs.

This is a human editing acceptance pass, not an unedited-model quality claim.
Only the isolated three-novel fixture databases may be used.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from easynovel.app import create_app
from easynovel.config import Settings

EDITS={
 'daily':{2:[
  ('两人一前一后把箱子抬上车斗。','两人一前一后把箱子抬到店门内侧的空地上，留待明早装车。'),
  ('陆遥正把“待定”箱往车斗上搬。','陆遥正把“待定”箱往门内空地上搬。'),
  ('陆遥跳下车斗，拍了拍手上的灰','陆遥从货架旁起身，拍了拍手上的灰'),
  ('陆遥站在车斗旁，没过来帮。','陆遥站在店门边，没过来帮。'),
  ('坐垫搁在上面，灰蓝色朝下，磨白的边角朝上。他走过去，翻了个面，灰蓝色朝上，边角朝下。','两个坐垫搁在上面。他走过去，把磨白的那一角推平。')]},
 'mystery':{1:[
  ('光斑里那枚指纹清晰得刺眼。','光斑里，灰痕边缘比纹路清楚。')],2:[
  ('那东西不是坐客车走的。是走的货。','如果那半句话说的是运东西，就值得查货运。但也可能是别的意思。'),
  ('父亲不是留了一把钥匙，是留了一个方向。','他忽然觉得，父亲留下的也许不只是一把钥匙。')]},
 'fantasy':{1:[
  ('她揣上铜板出门，在巷口油铺买了半壶劣质灯油。回来时天已经彻底暗了，风里带着湿冷的铁锈味。','她没再动陶罐里的铜板，从灶后翻出半壶旧灯油。等她拧开瓶塞，天已经彻底暗了。'),
  ('缴款凭条','未缴款的缴款联')],2:[
  ('昨天下午你讲妈把铃给我们那天的事，我记不太清。你再讲一遍。','昨天下午擦铃的时候，我们说了什么？我记不太清。你再讲一遍。'),
  ('阿杏说，妈把铃给我们那天下雨，我摔了一跤，铃滚进水沟，妈捞了半天。','阿杏说，她昨天下午讲妈说铃能镇邪；我笑她：锈成这样，镇什么邪。'),
  ('她自己的罚单昨夜已经烧了，可莫川这笔债，她一直知道，只是从没算清滚到了多少。','她的罚单还在陶罐旁，早晨城卫收了二十三枚，在缴款联上给余下五十七枚批了一天缓期。这笔二百四十枚的旧债却属于莫川，她一直知道，只是从没算清滚到了多少。')]}}

def exercise(case,root):
    folder=root/case; summary=json.loads((folder/'author-final/report.json').read_text(encoding='utf-8'))
    output=folder/'reader-approved'; output.mkdir(exist_ok=True)
    app=create_app(Settings(data_dir=folder/'data',token='line-edits',test_mode=True,legacy_path=folder/'absent.db'))
    report=[]
    with TestClient(app,headers={'Authorization':'Bearer line-edits'}) as c:
        def post(path,body):
            response=c.post('/api/v1'+path,json=body)
            if response.status_code!=200: raise RuntimeError(f'{case}: {response.status_code} {response.text[:200]}')
            return response.json()
        for row in summary:
            run=c.get('/api/v1/runs/'+row['run_id']).json(); pid=run['project_id']; cid=run['chapter_id']
            chapter=c.get('/api/v1/chapters/'+cid).json(); source=chapter['confirmed']; text=source['content']
            replacements=EDITS[case].get(row['number'],[])
            for before,after in replacements:
                if text.count(before)!=1: raise AssertionError(f'{case} chapter {row["number"]}: edit is not uniquely located')
                text=text.replace(before,after,1)
            revision=c.get('/api/v1/projects/'+pid).json()['revision']
            if replacements:
                version=post('/chapters/'+cid+'/versions',{'content':text,'source':'manual','parent_id':source['id'],'check_head':True,'expected_head_id':source['id'],'expected_revision':revision})
                post('/chapters/'+cid+'/impact',{'version_id':version['id'],'expected_revision':revision})
                accepted=[]
                for record in c.get('/api/v1/projects/'+pid+'/records?status=confirmed').json():
                    quote=record['data'].get('quote')
                    if record['source_version_id']!=source['id'] or not quote: continue
                    block=next((p for p in version['paragraphs'] if quote in p['text']),None)
                    if not block: continue
                    accepted.append({**record,'source_version_id':version['id'],'source_paragraph_id':block['id'],'status':'candidate'})
                post('/chapters/'+cid+'/commit',{'version_id':version['id'],'expected_revision':revision,'idempotency_key':'line-edit-'+version['id'],'memory_delta':accepted,'override_reason':'作者逐段核查的验收修订：物品交接、未缴罚单及最近24小时记忆，保留已核实证据。'})
            (output/f'chapter-{row["number"]}.md').write_text(text,encoding='utf-8')
            report.append({'number':row['number'],'characters':len(text),'author_line_edits':len(replacements),'model_run_id':run['id'],'status':'confirmed'})
        for impact in c.get('/api/v1/projects/'+pid+'/impact').json():
            if impact['status']=='applied':
                post('/impact/'+impact['id']+'/resolve',{'chapter_ids':[i['chapter_id'] for i in impact['items']],'expected_revision':c.get('/api/v1/projects/'+pid).json()['revision'],'reason':'作者逐段读过最终两章，核查过前章改写、物品位置、人物认知和时间，修复范围见验收改稿清单。'})
        export=c.get('/api/v1/projects/'+pid+'/export?format=md')
        if export.status_code!=200: raise AssertionError(export.text)
        (output/'novel.md').write_text(export.text,encoding='utf-8')
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    root=Path(sys.argv[1]).resolve()
    if root!=Path(__file__).resolve().parents[1]/'artifacts/acceptance-novels/2026-10-03-v2':
        raise SystemExit('Only the known isolated acceptance folder is allowed')
    for case in EDITS: print(json.dumps({'case':case,'chapters':exercise(case,root)},ensure_ascii=False))
