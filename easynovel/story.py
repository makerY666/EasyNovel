"""Only this service may turn candidate prose/memory into canon."""
import copy
import difflib
import hashlib
import json
import re
from fastapi import HTTPException
from sqlalchemy import text, func
from .database import Project, Chapter, Version, Record, Branch, Impact, Receipt, Job, dump, uid, now
from .schemas import RecordInput


def require(s, cls, identity):
    obj=s.get(cls,identity)
    if obj is None:
        raise HTTPException(404,'记录不存在')
    return obj


def revision(s,project_id,expected):
    p=require(s,Project,project_id)
    if p.revision != expected:
        raise HTTPException(409,{'message':'作品已改变，请刷新并重新审核；候选成果已保留。','revision':p.revision})
    return p


def require_branch(s,project_id,branch_id):
    if not s.query(Branch).filter_by(project_id=project_id,id=branch_id).first():
        raise HTTPException(404,'故事分支不存在')


def import_reservations(s,project_id,branch_id):
    """Pending imports own their chapter numbers across pauses and restarts."""
    ranges=[]
    for job in s.query(Job).filter_by(project_id=project_id,kind='import'):
        payload=job.payload or {}
        if job.status!='completed' and payload.get('branch_id','main')==branch_id and job.completed<job.total:
            first=payload.get('first_number')
            if isinstance(first,int): ranges.append((first+job.completed,first+job.total-1))
    return ranges


def next_chapter_number(s,project_id,branch_id):
    current=s.query(func.max(Chapter.number)).filter_by(project_id=project_id,branch_id=branch_id).scalar() or 0
    return max([current]+[end for _,end in import_reservations(s,project_id,branch_id)])+1


def tokenize(content):
    import jieba
    return ' '.join(t for t in jieba.cut_for_search(content) if t.strip())


def index_doc(s,doc_id,project_id,branch_id,title,content):
    s.execute(text('DELETE FROM search_fts WHERE doc_id=:id'),{'id':doc_id})
    s.execute(text('INSERT INTO search_fts(doc_id,project_id,branch_id,title,body) VALUES(:id,:pid,:bid,:title,:body)'),
              {'id':doc_id,'pid':project_id,'bid':branch_id,'title':tokenize(title),'body':tokenize(content)})


def paragraphs_for(content,previous=None):
    """Retain exact unchanged blocks; never guess a lock onto another paragraph."""
    lines=re.split(r'\n\s*\n',content.strip()) if content.strip() else []
    old=previous or []
    mapping={}
    matcher=difflib.SequenceMatcher(a=[p['text'] for p in old],b=lines,autojunk=False)
    for a,b,n in matcher.get_matching_blocks():
        for i in range(n):
            mapping[b+i]=old[a+i]
    return [{'id':mapping[i]['id'] if i in mapping else uid(),'text':value,'locked':mapping[i].get('locked',False) if i in mapping else False} for i,value in enumerate(lines)]


def verify_paragraphs(content,paragraphs):
    if len({p['id'] for p in paragraphs}) != len(paragraphs):
        raise HTTPException(422,'段落标识不能重复')
    if '\n\n'.join(p['text'] for p in paragraphs).strip() != content.strip():
        raise HTTPException(422,'正文与段落内容不一致')


def preserve_locks(previous,paragraphs):
    new={p['id']:p for p in paragraphs}
    for p in previous or []:
        if p.get('locked') and (p['id'] not in new or p['text'] != new[p['id']]['text']):
            raise HTTPException(409,'锁定段落发生变化，请先明确解除锁定再修改')


class StoryService:
    def __init__(self,db):
        self.db=db

    def create_project(self,body):
        with self.db.write() as s:
            p=Project(**body.model_dump())
            s.add(p); s.flush()
            s.add(Branch(project_id=p.id,id='main',name='主线'))
            return dump(p)

    def create_chapter(self,pid,body):
        with self.db.write() as s:
            p=require(s,Project,pid)
            require_branch(s,pid,body.branch_id)
            number=body.number or next_chapter_number(s,pid,body.branch_id)
            if any(start<=number<=end for start,end in import_reservations(s,pid,body.branch_id)):
                raise HTTPException(409,'章节序号正在被导入任务预留，请选择其他序号或完成导入')
            if s.query(Chapter).filter_by(project_id=pid,branch_id=body.branch_id,number=number).first():
                raise HTTPException(409,'章节序号已存在')
            c=Chapter(project_id=pid,title=body.title,number=number,branch_id=body.branch_id,story_time=body.story_time if body.story_time is not None else number)
            s.add(c); p.revision+=1; s.flush()
            return dump(c)

    def save_version(self,cid,body):
        with self.db.write() as s:
            c=require(s,Chapter,cid)
            revision(s,c.project_id,body.expected_revision)
            parent_id=body.parent_id or c.draft_version_id or c.confirmed_version_id
            head=c.draft_version_id or c.confirmed_version_id
            if body.check_head and head!=body.expected_head_id:
                raise HTTPException(409,'草稿在生成期间已改变，候选成果保留在任务中；请比较版本')
            if body.parent_id and head and body.parent_id!=head:
                raise HTTPException(409,'草稿版本已更新，当前候选保留；请重新载入并比较版本')
            parent=require(s,Version,parent_id) if parent_id else None
            if parent and parent.chapter_id != cid:
                raise HTTPException(422,'父版本属于另一章节')
            paragraphs=[p.model_dump() for p in body.paragraphs] if body.paragraphs is not None else paragraphs_for(body.content,parent.paragraphs if parent else [])
            verify_paragraphs(body.content,paragraphs)
            # Authors can explicitly unlock a block by preserving its text and clearing locked.
            if body.source=='ai' and parent:
                preserve_locks(parent.paragraphs,paragraphs)
            v=Version(chapter_id=cid,content=body.content,paragraphs=paragraphs,source=body.source,parent_id=parent_id)
            s.add(v); s.flush()
            c.draft_version_id=v.id; c.updated_at=now()
            return dump(v)

    def validate_record(self,s,pid,body,allow_pending_version=None):
        require_branch(s,pid,body.branch_id)
        if body.status=='confirmed' and body.source_type!='author' and not body.source_version_id:
            raise HTTPException(422,'正文事实、人物言论与模型推断确认时必须提供正文证据')
        for dep in body.dependencies:
            r=require(s,Record,dep)
            if r.project_id != pid or r.branch_id != body.branch_id:
                raise HTTPException(422,'依赖不能跨作品或分支')
        if body.source_version_id:
            v=require(s,Version,body.source_version_id); c=require(s,Chapter,v.chapter_id)
            if c.project_id!=pid or c.branch_id!=body.branch_id:
                raise HTTPException(422,'证据来源不能跨作品或分支')
            if body.source_paragraph_id and body.source_paragraph_id not in {p['id'] for p in v.paragraphs}:
                raise HTTPException(422,'证据段落不存在')
            if body.status=='confirmed' and c.confirmed_version_id!=v.id and v.id!=allow_pending_version:
                raise HTTPException(409,'来源正文尚未确认，不能确认对应记忆')
        if body.kind=='knowledge' and not body.data.get('character_id'):
            raise HTTPException(422,'人物认知需要 character_id')
        if body.kind=='foreshadow' and body.data.get('status')=='resolved':
            if not body.source_version_id or not body.data.get('payoff_evidence'):
                raise HTTPException(422,'回收伏笔需要正文来源和 payoff_evidence')

    def add_record(self,pid,body,expected=None):
        with self.db.write() as s:
            p=revision(s,pid,expected) if expected is not None else require(s,Project,pid)
            self.validate_record(s,pid,body)
            r=Record(project_id=pid,**body.model_dump()); s.add(r); s.flush()
            if r.kind=='character': r.data={**r.data,'entity_id':r.id}
            if r.status=='confirmed':
                p.revision+=1
                index_doc(s,r.id,pid,r.branch_id,r.title,r.content)
            return dump(r)

    def record_impact(self,rid):
        with self.db.write() as s:
            r=require(s,Record,rid); p=require(s,Project,r.project_id)
            old=require(s,Record,r.supersedes_id) if r.supersedes_id else r
            seed={old.id}
            rows=s.query(Record).filter_by(project_id=r.project_id,branch_id=r.branch_id,status='confirmed').all()
            while True:
                additions={x.id for x in rows if set(x.dependencies)&seed}-seed
                if not additions: break
                seed.update(additions)
            direct={x.source_version_id for x in rows if x.id in seed and x.source_version_id}
            items=[]
            for c in s.query(Chapter).filter_by(project_id=r.project_id,branch_id=r.branch_id).order_by(Chapter.number):
                if c.story_time<old.valid_from: continue
                items.append({'chapter_id':c.id,'number':c.number,'title':c.title,'kind':'direct' if c.confirmed_version_id in direct else 'inferred','reason':'依赖已变更的设定' if c.confirmed_version_id in direct else '设定变更可能影响本章，需核查','entities':old.entity_ids})
            imp=Impact(project_id=r.project_id,source_record_id=r.id,base_revision=p.revision,items=items,coverage='检查显式依赖，并保守列出生效时间后的章节；作者需复核文学影响。')
            s.add(imp); s.flush(); return dump(imp)

    def apply_record_impact(self,s,r,p,acknowledged):
        imp=s.query(Impact).filter_by(source_record_id=r.id,base_revision=p.revision,status='analyzed').order_by(Impact.created_at.desc()).first()
        if not imp: raise HTTPException(409,'请先预览设定修改的影响')
        if imp.items and not acknowledged: raise HTTPException(409,'请明确确认影响范围，受影响章节将暂停正式续写')
        for item in imp.items: require(s,Chapter,item['chapter_id']).blocked=True
        imp.status='applied' if imp.items else 'resolved'

    def approve_record(self,rid,expected,impact_acknowledged=False):
        with self.db.write() as s:
            r=require(s,Record,rid); p=revision(s,r.project_id,expected)
            if r.status=='confirmed':
                return dump(r)
            if r.status!='candidate':
                raise HTTPException(409,'只有候选资料可以确认')
            body=RecordInput.model_validate({**dump(r),'status':'confirmed'})
            self.validate_record(s,r.project_id,body)
            if r.supersedes_id:
                old=require(s,Record,r.supersedes_id)
                if old.status!='confirmed': raise HTTPException(409,'原设定已改变，请重新建立候选')
                self.apply_record_impact(s,r,p,impact_acknowledged)
                old.status='superseded'
                s.execute(text('DELETE FROM search_fts WHERE doc_id=:id'),{'id':old.id})
            r.status='confirmed'; p.revision+=1
            index_doc(s,r.id,r.project_id,r.branch_id,r.title,r.content)
            return dump(r)

    def replace_record(self,rid,changes):
        with self.db.write() as s:
            old=require(s,Record,rid); p=revision(s,old.project_id,changes.pop('expected_revision'))
            values={**dump(old),**changes}; values['status']='candidate'
            if old.kind=='character': values['data']={**values['data'],'entity_id':old.data.get('entity_id',old.id)}
            body=RecordInput.model_validate(values)
            if body.branch_id!=old.branch_id or body.kind!=old.kind:
                raise HTTPException(422,'资料替换不能改变所属分支或类型，请另建候选资料')
            self.validate_record(s,old.project_id,body)
            r=Record(project_id=old.project_id,supersedes_id=old.id,**body.model_dump())
            s.add(r); s.flush()
            result=dump(r)
        result['impact']=self.record_impact(r.id)
        return result

    def records(self,pid,branch='main',kind=None,status=None,entity=None,story_time=None):
        with self.db.read() as s:
            require(s,Project,pid)
            q=s.query(Record).filter_by(project_id=pid,branch_id=branch)
            if kind: q=q.filter_by(kind=kind)
            if status: q=q.filter_by(status=status)
            if story_time is not None:
                q=q.filter(Record.valid_from<=story_time,(Record.valid_until.is_(None))|(Record.valid_until>story_time))
            rows=q.order_by(Record.created_at).all()
            return [dump(r) for r in rows if not entity or entity in r.entity_ids or entity==r.data.get('character_id')]

    def impact(self,cid,version_id,expected):
        with self.db.write() as s:
            c=require(s,Chapter,cid); revision(s,c.project_id,expected)
            v=require(s,Version,version_id)
            if v.chapter_id!=cid: raise HTTPException(422,'版本不属于本章')
            old=require(s,Version,c.confirmed_version_id) if c.confirmed_version_id else None
            source_records=s.query(Record).filter_by(project_id=c.project_id,branch_id=c.branch_id,source_version_id=c.confirmed_version_id,status='confirmed').all() if old else []
            seed={r.id for r in source_records}
            all_records=s.query(Record).filter_by(project_id=c.project_id,branch_id=c.branch_id,status='confirmed').all()
            changed=True
            while changed:
                additions={r.id for r in all_records if r.id not in seed and set(r.dependencies)&seed}
                changed=bool(additions); seed.update(additions)
            direct_versions={r.source_version_id for r in all_records if r.id in seed and r.source_version_id}
            entities={x for r in source_records for x in r.entity_ids}
            # Conservatively include successors: dependency extraction is not a proof of completeness.
            items=[]
            if old and old.content!=v.content:
                for nxt in s.query(Chapter).filter(Chapter.project_id==c.project_id,Chapter.branch_id==c.branch_id,Chapter.number>c.number).order_by(Chapter.number):
                    direct=nxt.confirmed_version_id in direct_versions
                    items.append({'chapter_id':nxt.id,'number':nxt.number,'title':nxt.title,'kind':'direct' if direct else 'inferred','reason':'依赖已变更的正文证据' if direct else '前文变化可能影响后文，请核查因果与人物认知','entities':list(entities)})
            imp=Impact(project_id=c.project_id,source_chapter_id=cid,version_id=v.id,base_revision=expected,items=items,coverage='已检查来源记录与显式依赖；其余后续章节列为推测影响，文学影响需作者复核。')
            s.add(imp); s.flush()
            return dump(imp)

    def commit(self,cid,body,*,reviewed_repair=False):
        fingerprint=hashlib.sha256(json.dumps({'chapter_id':cid,**body.model_dump()},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        with self.db.write() as s:
            receipt=s.get(Receipt,body.idempotency_key)
            if receipt:
                if receipt.payload_hash!=fingerprint: raise HTTPException(409,'幂等键已用于不同提交')
                return receipt.result
            c=require(s,Chapter,cid); p=revision(s,c.project_id,body.expected_revision)
            v=require(s,Version,body.version_id)
            if v.chapter_id!=cid: raise HTTPException(422,'版本不属于本章')
            if c.blocked and not body.override_reason and not reviewed_repair:
                raise HTTPException(409,'本章受到前文修改影响，请审核修复或填写确认说明')
            imp=None
            if c.confirmed_version_id and c.confirmed_version_id!=v.id:
                imp=s.query(Impact).filter_by(source_chapter_id=cid,version_id=v.id,base_revision=p.revision).order_by(Impact.created_at.desc()).first()
                if not imp: raise HTTPException(409,'修改已确认正文前必须先分析影响')
                for item in imp.items:
                    require(s,Chapter,item['chapter_id']).blocked=True
                imp.status='applied'
                for old in s.query(Record).filter_by(source_version_id=c.confirmed_version_id,status='confirmed'):
                    old.status='superseded'
                    s.execute(text('DELETE FROM search_fts WHERE doc_id=:id'),{'id':old.id})
            for item in body.memory_delta:
                if item.branch_id!=c.branch_id: raise HTTPException(422,'记忆属于另一故事分支')
                item=item.model_copy(update={'status':'confirmed','source_version_id':v.id if item.source_type!='author' else item.source_version_id})
                self.validate_record(s,c.project_id,item,allow_pending_version=v.id)
                r=Record(project_id=c.project_id,**item.model_dump()); s.add(r); s.flush()
                index_doc(s,r.id,c.project_id,c.branch_id,r.title,r.content)
            for rid in body.accepted_memory_ids:
                r=require(s,Record,rid)
                if r.project_id!=c.project_id or r.branch_id!=c.branch_id or r.status!='candidate': raise HTTPException(422,'候选记忆不属于本作品或已经处理')
                if r.supersedes_id: raise HTTPException(409,'设定替换需要单独审核其影响，不能通过正文记忆提交绕过')
                self.validate_record(s,c.project_id,RecordInput.model_validate({**dump(r),'status':'confirmed'}),allow_pending_version=v.id)
                r.status='confirmed'
                index_doc(s,r.id,c.project_id,c.branch_id,r.title,r.content)
            if c.confirmed_version_id and c.confirmed_version_id!=v.id:
                require(s,Version,c.confirmed_version_id).status='superseded'
            v.status='confirmed'; c.confirmed_version_id=v.id; c.blocked=False; c.updated_at=now()
            p.revision+=1
            index_doc(s,c.id,c.project_id,c.branch_id,c.title,v.content)
            result={'version':dump(v),'revision':p.revision,'impact':dump(imp) if imp else None}
            s.add(Receipt(key=body.idempotency_key,project_id=p.id,payload_hash=fingerprint,result=result))
            return result

    def resolve_impact(self,identity,body):
        if not body.get('reason','').strip(): raise HTTPException(422,'需要填写核查说明')
        with self.db.write() as s:
            i=require(s,Impact,identity); p=revision(s,i.project_id,body['expected_revision'])
            if i.status not in ('applied','resolved'): raise HTTPException(409,'只有已应用的影响可以解除')
            allowed={v['chapter_id'] for v in i.items}
            selected=set(body.get('chapter_ids',[]))
            if not selected<=allowed: raise HTTPException(422,'所选章节不在影响范围')
            resolved=set(i.resolved_ids)|selected
            i.resolved_ids=list(resolved)
            for cid in selected:
                other=s.query(Impact).filter(Impact.project_id==i.project_id,Impact.status=='applied',Impact.id!=i.id).all()
                if not any(cid in {x['chapter_id'] for x in ximp.items}-set(ximp.resolved_ids) for ximp in other):
                    require(s,Chapter,cid).blocked=False
            if resolved>=allowed: i.status='resolved'
            p.revision+=1
            return dump(i)

    def fork(self,pid,name,source='main'):
        with self.db.write() as s:
            p=require(s,Project,pid); require_branch(s,pid,source)
            b=Branch(project_id=pid,id=uid(),name=name); s.add(b); s.flush()
            version_map={}; record_map={}; copies=[]
            for old in s.query(Chapter).filter_by(project_id=pid,branch_id=source).all():
                c=Chapter(id=uid(),project_id=pid,branch_id=b.id,number=old.number,title=old.title,story_time=old.story_time,blocked=old.blocked)
                s.add(c)
                for old_id in dict.fromkeys([old.confirmed_version_id,old.draft_version_id]):
                    if old_id:
                        ov=require(s,Version,old_id)
                        v=Version(id=uid(),chapter_id=c.id,content=ov.content,paragraphs=copy.deepcopy(ov.paragraphs),source=ov.source,status=ov.status)
                        version_map[old_id]=v.id; s.add(v)
                c.confirmed_version_id=version_map.get(old.confirmed_version_id); c.draft_version_id=version_map.get(old.draft_version_id)
                if c.confirmed_version_id:
                    index_doc(s,c.id,pid,b.id,c.title,require(s,Version,old.confirmed_version_id).content)
            for old in s.query(Record).filter_by(project_id=pid,branch_id=source).all():
                values=dump(old); values.update(id=uid(),branch_id=b.id,source_version_id=version_map.get(old.source_version_id),supersedes_id=None,created_at=now())
                if old.source_version_id and not values['source_version_id']: continue
                record_map[old.id]=values['id']; copies.append(values)
            for values in copies:
                values['dependencies']=[record_map[x] for x in values['dependencies'] if x in record_map]
                values['entity_ids']=[record_map.get(x,x) for x in values['entity_ids']]
                if values['data'].get('character_id'):
                    values['data']={**values['data'],'character_id':record_map.get(values['data']['character_id'],values['data']['character_id'])}
                if values['data'].get('entity_id'):
                    values['data']={**values['data'],'entity_id':record_map.get(values['data']['entity_id'],values['data']['entity_id'])}
                s.add(Record(**values))
                if values['status']=='confirmed': index_doc(s,values['id'],pid,b.id,values['title'],values['content'])
            p.revision+=1
            return dump(b)
