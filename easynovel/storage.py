import asyncio
import json
import re
import sqlite3
import zipfile
from contextlib import closing
from pathlib import Path
from fastapi import HTTPException
from .database import Project, Chapter, Version, Record, Job, Run, Branch, dump, uid, now
from .story import require, require_branch, index_doc, paragraphs_for, next_chapter_number


def decode_novel(content):
    for encoding in ('utf-8-sig','utf-16','gb18030'):
        try:
            decoded=content.decode(encoding)
            if '\x00' in decoded: continue
            return decoded.replace('\r\n','\n').replace('\r','\n'),encoding
        except UnicodeError: continue
    raise HTTPException(422,'无法识别文件编码，请转为 UTF-8')


def split_novel(content):
    pattern=re.compile(r'^(?:#{1,3}\s+.+|第[零〇一二三四五六七八九十百千万两\d]+[章节回卷部]\s*[^\n]*|Chapter\s+\d+[^\n]*)$',re.MULTILINE|re.IGNORECASE)
    headings=list(pattern.finditer(content)); chapters=[]
    if not headings: return [{'title':'导入正文','content':content.strip()}]
    prefix=content[:headings[0].start()].strip()
    if prefix: chapters.append({'title':'序言','content':prefix})
    for i,h in enumerate(headings):
        body=content[h.end():headings[i+1].start() if i+1<len(headings) else len(content)].strip()
        chapters.append({'title':h.group().lstrip('#').strip(),'content':body})
    return chapters


class Storage:
    def __init__(self,db,settings):
        self.db=db; self.settings=settings; self.tasks={}

    def start_import(self,pid,body):
        chapters=body.get('chapters',[])
        if not chapters or len(chapters)>20000: raise HTTPException(422,'需要 1 至 20000 个章节')
        for item in chapters:
            if not isinstance(item.get('title'),str) or not item['title'].strip() or not isinstance(item.get('content'),str) or len(item['content'])>500000:
                raise HTTPException(422,'章节标题或正文无效，请检查分章')
        with self.db.write() as s:
            require(s,Project,pid); branch=body.get('branch_id','main'); require_branch(s,pid,branch)
            # Reserve numbers once, so pause/resume cannot interleave numbering with new chapters.
            first=next_chapter_number(s,pid,branch)
            j=Job(project_id=pid,kind='import',total=len(chapters),payload={'chapters':chapters,'branch_id':branch,'first_number':first})
            s.add(j); s.flush(); result=dump(j)
        self.schedule(j.id)
        return {k:v for k,v in result.items() if k!='payload'}

    def schedule(self,jid):
        if jid in self.tasks and not self.tasks[jid].done(): return
        self.tasks[jid]=asyncio.create_task(self.import_job(jid))

    async def import_job(self,jid):
        try:
            while True:
                with self.db.write() as s:
                    j=require(s,Job,jid)
                    if j.status=='paused': return
                    if j.completed>=j.total:
                        j.status='completed'; return
                    j.status='running'; item=j.payload['chapters'][j.completed]
                    number=j.payload['first_number']+j.completed
                    if s.query(Chapter).filter_by(project_id=j.project_id,branch_id=j.payload['branch_id'],number=number).first(): raise HTTPException(409,'导入预留序号被占用，请在新分支重新导入')
                    c=Chapter(id=uid(),project_id=j.project_id,branch_id=j.payload['branch_id'],number=number,title=item['title'],story_time=number)
                    v=Version(id=uid(),chapter_id=c.id,content=item['content'],paragraphs=paragraphs_for(item['content']),source='import',status='confirmed')
                    c.confirmed_version_id=v.id; c.draft_version_id=v.id
                    s.add_all([c,v]); require(s,Project,j.project_id).revision+=1
                    index_doc(s,c.id,j.project_id,c.branch_id,c.title,v.content)
                    j.completed+=1
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            with self.db.write() as s: require(s,Job,jid).status='paused'
        except Exception as exc:
            with self.db.write() as s:
                j=require(s,Job,jid); j.status='failed'; j.error=str(exc.detail) if isinstance(exc,HTTPException) else '导入中断，已导入章节保留'

    def backups(self):
        folder=self.settings.data_dir/'backups'; folder.mkdir(exist_ok=True)
        items=[]
        for f in sorted(folder.glob('*.zip'),key=lambda x:x.stat().st_mtime,reverse=True):
            try:
                with zipfile.ZipFile(f) as z: manifest=json.loads(z.read('manifest.json'))
                items.append(manifest)
            except (ValueError,zipfile.BadZipFile,KeyError): continue
        return items

    def backup(self,automatic=False):
        folder=self.settings.data_dir/'backups'; folder.mkdir(exist_ok=True)
        identity=uid(); name=('automatic-' if automatic else 'manual-')+identity+'.zip'
        staging=folder/(identity+'.sqlite3')
        checkpoints=folder/(identity+'-checkpoints.sqlite3')
        with closing(sqlite3.connect(self.db.path)) as schema_db:
            schema=schema_db.execute('SELECT version_num FROM alembic_version').fetchone()[0]
        meta={'id':identity,'name':name,'created_at':now(),'automatic':automatic,'schema':schema,'version':'0.2.0'}
        try:
            with self.db.lock:
                with closing(sqlite3.connect(self.db.path)) as src,closing(sqlite3.connect(staging)) as dst: src.backup(dst)
                graph=self.settings.data_dir/'checkpoints.sqlite3'
                if graph.exists():
                    with closing(sqlite3.connect(graph)) as src,closing(sqlite3.connect(checkpoints)) as dst: src.backup(dst)
                with zipfile.ZipFile(folder/name,'w',zipfile.ZIP_DEFLATED) as z:
                    z.write(staging,'studio.sqlite3')
                    if checkpoints.exists(): z.write(checkpoints,'checkpoints.sqlite3')
                    z.writestr('manifest.json',json.dumps(meta,ensure_ascii=False))
        finally:
            staging.unlink(missing_ok=True); checkpoints.unlink(missing_ok=True)
        automatic_files=[v for v in self.backups() if v.get('automatic')]
        for item in automatic_files[7:]: (folder/item['name']).unlink(missing_ok=True)
        return meta

    def backup_path(self,identity):
        meta=next((m for m in self.backups() if m['id']==identity),None)
        if not meta: raise HTTPException(404,'备份不存在')
        return self.settings.data_dir/'backups'/meta['name']

    def restore(self,identity):
        path=self.backup_path(identity)
        with zipfile.ZipFile(path) as z:
            manifest=json.loads(z.read('manifest.json'))
            if manifest.get('schema') not in ('0001','0002','0003'): raise HTTPException(422,'备份数据库版本不兼容')
            candidate=self.settings.data_dir/'restore.sqlite3'
            candidate.write_bytes(z.read('studio.sqlite3'))
            try:
                with closing(sqlite3.connect(candidate)) as conn:
                    if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise HTTPException(422,'备份数据库损坏')
                    conn.execute('SELECT id FROM projects LIMIT 1')
                self.db.engine.dispose()
                for suffix in ('-wal','-shm'): Path(str(self.db.path)+suffix).unlink(missing_ok=True)
                candidate.replace(self.db.path)
                graph=self.settings.data_dir/'checkpoints.sqlite3'
                for suffix in ('-wal','-shm'): Path(str(graph)+suffix).unlink(missing_ok=True)
                if 'checkpoints.sqlite3' in z.namelist(): graph.write_bytes(z.read('checkpoints.sqlite3'))
                else: graph.unlink(missing_ok=True)
            finally: candidate.unlink(missing_ok=True)
        self.db.initialize()
        return {'ok':True}

    def import_legacy(self):
        legacy=self.settings.legacy_path
        if not legacy.exists(): raise HTTPException(404,'没有检测到旧数据库')
        legacy_backup=self.settings.data_dir/'backups'/('legacy-'+uid()+'.sqlite3')
        legacy_backup.parent.mkdir(exist_ok=True)
        with closing(sqlite3.connect(f'file:{legacy.as_posix()}?mode=ro',uri=True)) as src,closing(sqlite3.connect(legacy_backup)) as dst: src.backup(dst)
        count=0; projects=[]
        with closing(sqlite3.connect(f'file:{legacy.as_posix()}?mode=ro',uri=True)) as src,self.db.write() as s:
            src.row_factory=sqlite3.Row
            tables={r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'novels' not in tables: raise HTTPException(422,'旧数据库没有可识别的 novels 表')
            for old in src.execute('SELECT * FROM novels'):
                old=dict(old); marker='legacy:'+str(legacy.resolve())+':'+str(old['id'])
                if any(p.settings.get('legacy_source')==marker for p in s.query(Project)):
                    continue
                p=Project(title=old.get('title') or '旧作品',genre=old.get('genre') or '',description=old.get('synopsis') or '',settings={'legacy_source':marker})
                s.add(p); s.flush(); s.add(Branch(project_id=p.id,id='main',name='主线')); projects.append(p.id)
                chapter_map={}; version_map={}
                if 'chapters' in tables:
                    for row in src.execute('SELECT * FROM chapters WHERE novel_id=? ORDER BY chapter_number',(old['id'],)):
                        data=dict(row); c=Chapter(project_id=p.id,title=data.get('title') or '未命名',number=data['chapter_number'],story_time=data['chapter_number'])
                        s.add(c); s.flush(); chapter_map[data['id']]=c.id
                        content=''
                        if 'chapter_versions' in tables:
                            item=src.execute('SELECT * FROM chapter_versions WHERE chapter_id=? ORDER BY version_number DESC LIMIT 1',(data['id'],)).fetchone()
                            if item: content=dict(item).get('content','')
                        if not content: content=data.get('content') or ''
                        if content:
                            v=Version(chapter_id=c.id,content=content,paragraphs=paragraphs_for(content),source='import',status='draft')
                            s.add(v); s.flush(); c.draft_version_id=v.id; version_map[data['id']]=v.id
                        count+=1
                        if data.get('summary'):
                            s.add(Record(project_id=p.id,kind='summary',title=c.title+' 旧摘要',content=data['summary'],status='candidate',source_type='inference',source_version_id=version_map.get(data['id']),data={'legacy':True}))
                for table,kind in [('characters','character'),('world_rules','rule'),('timeline_events','event'),('foreshadowings','foreshadow'),('style_guides','directive')]:
                    if table not in tables: continue
                    for row in src.execute('SELECT * FROM '+table+' WHERE novel_id=?',(old['id'],)):
                        data=dict(row); title=data.get('name') or data.get('rule_id') or data.get('foreshadowing_id') or '旧资料'
                        # Legacy provenance is not upgraded into confirmed facts.
                        s.add(Record(project_id=p.id,kind=kind,title=title,content=data.get('content') or json.dumps(data,ensure_ascii=False),status='candidate',source_type='inference',data={'legacy':data}))
        return {'projects':projects,'count':count,'backup':legacy_backup.name}

    async def shutdown(self):
        for task in self.tasks.values():
            if not task.done(): task.cancel()
        await asyncio.gather(*self.tasks.values(),return_exceptions=True)
