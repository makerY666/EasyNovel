"""Repeatable synthetic local storage/retrieval benchmark; no paid calls."""
import json
import math
import platform
import statistics
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from easynovel.database import Database,Project,Branch,Chapter,Version,Record,uid,dump
from easynovel.story import tokenize
from easynovel.retrieval import Retrieval
from easynovel.schemas import ContextInput


def measure(action,count=50):
    for _ in range(3): action()
    values=[]
    for _ in range(count):
        start=time.perf_counter(); action(); values.append((time.perf_counter()-start)*1000)
    return {'p50_ms':round(statistics.median(values),2),'p95_ms':round(sorted(values)[math.ceil(len(values)*.95)-1],2),'samples':count}


def main():
    folder=Path('artifacts/benchmark')/uid(); folder.mkdir(parents=True)
    db=Database(folder/'studio.sqlite3'); db.initialize(); pid=uid()
    started=time.perf_counter()
    template='船靠近旧城，雨水沿着船舷流下。众人听见钟声，各自整理行囊。'
    prose=(template*120)[:3000]; text_index=tokenize(prose)
    chapters=[]; versions=[]; docs=[]
    for n in range(1,5001):
        cid=uid(); vid=uid(); title=f'第{n}章 旧城'
        content=prose if n!=18 else '林舟把玉佩交给苏雨。玉佩刻痕指向旧城。'+prose[25:]
        chapters.append({'id':cid,'project_id':pid,'branch_id':'main','number':n,'title':title,'story_time':n,'confirmed_version_id':vid})
        versions.append({'id':vid,'chapter_id':cid,'content':content,'paragraphs':[{'id':uid(),'text':content,'locked':False}],'status':'confirmed','source':'author'})
        docs.append((cid,pid,'main',tokenize(title),text_index if n!=18 else tokenize(content)))
    with db.write() as s:
        s.add(Project(id=pid,title='规模验收',revision=1)); s.add(Branch(project_id=pid,id='main',name='主线'))
        s.execute(Chapter.__table__.insert(),chapters); s.execute(Version.__table__.insert(),versions)
    for batch in range(0,100000,2000):
        rows=[]
        for i in range(batch,batch+2000):
            identity=uid(); content=f'道具编号{i}在第{i%5000+1}章被发现，归属人物{i%600}。'
            rows.append({'id':identity,'project_id':pid,'branch_id':'main','kind':'event','title':f'道具编号{i}','content':content,'status':'confirmed','source_type':'author','entity_ids':[f'人物{i%600}'],'valid_from':i%5000+1})
            docs.append((identity,pid,'main',f'道具 编号 {i}',f'道具 编号 {i} 发现 归属 人物 {i%600}'))
        with db.write() as s: s.execute(Record.__table__.insert(),rows)
    with db.engine.begin() as conn:
        conn.exec_driver_sql('INSERT INTO search_fts(doc_id,project_id,branch_id,title,body) VALUES(?,?,?,?,?)',docs)
    from easynovel.story import StoryService
    from easynovel.schemas import RecordInput
    story=StoryService(db)
    promise=story.add_record(pid,RecordInput(kind='foreshadow',title='玉佩来源',content='苏雨保管林舟交给她的玉佩',source_type='text',source_version_id=versions[17]['id'],source_paragraph_id=versions[17]['paragraphs'][0]['id'],status='confirmed',data={'payoff_start':2300,'status':'open'}))
    retrieval=Retrieval(db,folder); target=chapters[-1]
    def open_chapter():
        with db.read() as s:
            chapter=s.get(Chapter,target['id']); version=s.get(Version,chapter.confirmed_version_id)
            json.dumps({**dump(chapter),'confirmed':dump(version)},ensure_ascii=False)
    search=measure(lambda:retrieval.search(pid,'玉佩'))
    context=measure(lambda:retrieval.context(pid,ContextInput(chapter_id=target['id'],task='回收玉佩刻痕',entities=['人物1'],token_limit=12000)),count=20)
    pack=retrieval.context(pid,ContextInput(chapter_id=target['id'],task='回收玉佩刻痕'))
    report={'platform':platform.platform(),'python':platform.python_version(),'chapter_count':5000,'prose_characters':sum(len(v['content']) for v in versions),'record_count':100001,'fts_documents':105001,'generation_seconds':round(time.perf_counter()-started,2),'open_chapter':measure(open_chapter),'local_search':search,'context':context,'long_range_promise_recalled':promise['id'] in {x['id'] for x in pack['evidence']},'scope':'预热本地 SQLite/FTS 与上下文；不包含远程嵌入、浏览器渲染或文学评价'}
    (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    Path('artifacts/benchmark/latest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
