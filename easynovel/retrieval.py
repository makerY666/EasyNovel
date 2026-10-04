import json
import math
import re
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import text, or_, Text
from .database import Chapter, Version, Record, Project, dump
from .story import require, require_branch, tokenize


def tokens(value):
    """Conservative UTF-8 upper estimate; provider usage replaces this after completion."""
    content=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
    return len(content.encode('utf-8'))+32


class Retrieval:
    def __init__(self,db,data_dir):
        self.db=db; self.data_dir=data_dir
        self.semantic_providers={}
        registry=self.data_dir/'vector_registry.json'
        if registry.exists():
            try:
                self.semantic_providers={(v['project_id'],v['branch_id']):v['provider'] for v in json.loads(registry.read_text(encoding='utf-8'))}
            except (ValueError,KeyError): pass

    def register(self,pid,branch,provider):
        self.semantic_providers[(pid,branch)]=provider
        registry=self.data_dir/'vector_registry.json'; temporary=registry.with_suffix('.tmp')
        temporary.write_text(json.dumps([{'project_id':p,'branch_id':b,'provider':v} for (p,b),v in self.semantic_providers.items()],ensure_ascii=False),encoding='utf-8')
        temporary.replace(registry)

    def active(self,s,r,story_time=None,before_number=None):
        if r.status!='confirmed': return False
        visited={r.id}; pending=list(r.dependencies)
        while pending:
            identity=pending.pop()
            if identity in visited: continue
            visited.add(identity); dependency=s.get(Record,identity)
            if not dependency or dependency.status!='confirmed': return False
            if story_time is not None and (dependency.valid_from>story_time or (dependency.valid_until is not None and dependency.valid_until<=story_time)): return False
            if dependency.source_version_id:
                source=s.get(Version,dependency.source_version_id)
                chapter=s.get(Chapter,source.chapter_id) if source else None
                if not chapter or chapter.blocked or chapter.confirmed_version_id!=source.id: return False
                if before_number is not None and chapter.number>=before_number: return False
            pending.extend(dependency.dependencies)
        if story_time is not None and (r.valid_from>story_time or (r.valid_until is not None and r.valid_until<=story_time)): return False
        if r.source_version_id:
            v=s.get(Version,r.source_version_id)
            c=s.get(Chapter,v.chapter_id) if v else None
            if not c or c.confirmed_version_id!=v.id or c.blocked: return False
            if before_number is not None and c.number>=before_number: return False
        return True

    def search(self,pid,q,branch='main',story_time=None,limit=20,before_number=None):
        parts=[x for x in tokenize(q).split() if re.search(r'\w',x)]
        expression=' OR '.join('"'+x.replace('"','""')+'"' for x in dict.fromkeys(parts[:30]))
        results=[]
        with self.db.read() as s:
            require(s,Project,pid)
            rows=s.execute(text('SELECT doc_id, bm25(search_fts) AS rank FROM search_fts WHERE search_fts MATCH :q AND project_id=:p AND branch_id=:b ORDER BY rank LIMIT :n'),{'q':expression,'p':pid,'b':branch,'n':max(limit*5,100)}).all() if expression else []
            seen=set()
            for identity,score in rows:
                r=s.get(Record,identity)
                if r and self.active(s,r,story_time,before_number) and r.kind not in ('plan','directive'):
                    item=dump(r); item['reason']='全文与实体关键词匹配'; item['score']=-score; results.append(item); seen.add(identity)
                elif not r:
                    c=s.get(Chapter,identity)
                    if not c or c.blocked or not c.confirmed_version_id: continue
                    if before_number is not None and c.number>=before_number: continue
                    if story_time is not None and c.story_time>story_time: continue
                    v=s.get(Version,c.confirmed_version_id)
                    for block in v.paragraphs:
                        if any(p in block['text'] for p in parts):
                            results.append({'id':c.id+':'+block['id'],'kind':'text','title':f'第{c.number}章 {c.title}','content':block['text'],'source_version_id':v.id,'source_paragraph_id':block['id'],'reason':'已确认正文关键词匹配','score':-score})
                            if len(results)>=limit: break
            # Explicit entity aliases add candidates even when segmentation differs.
            for r in s.query(Record).filter_by(project_id=pid,branch_id=branch,status='confirmed',kind='character'):
                if r.id in seen or not self.active(s,r,story_time,before_number): continue
                aliases=[r.title,*r.data.get('aliases',[])]
                if any(alias and alias in q for alias in aliases):
                    results.insert(0,{**dump(r),'reason':'人物名称或已确认别名匹配','score':1.0})
            return {'items':results[:limit],'semantic_search':bool(self.semantic_providers.get((pid,branch)))}

    def context(self,pid,body,*,for_repair=False):
        with self.db.read() as s:
            c=require(s,Chapter,body.chapter_id); p=require(s,Project,pid)
            if c.project_id!=pid: raise HTTPException(422,'章节属于另一作品')
            if c.blocked and not for_repair: raise HTTPException(409,'本章有待处理的前文影响，正式续写暂停')
            t=body.story_time if body.story_time is not None else c.story_time
            base=s.query(Record).filter_by(project_id=pid,branch_id=c.branch_id,status='confirmed').filter(Record.valid_from<=t,or_(Record.valid_until.is_(None),Record.valid_until>t))
            characters=[r for r in base.filter(Record.kind=='character') if self.active(s,r,t,c.number)]
            entity_set=set(body.entities)
            for r in characters:
                if r.kind=='character' and (r.id in entity_set or r.data.get('entity_id') in entity_set or any(x and x in body.task for x in [r.title,*r.data.get('aliases',[])])):
                    entity_set.add(r.id); entity_set.add(r.data.get('entity_id',r.id)); entity_set.add(r.title)
            pov=next((r.data.get('entity_id',r.id) for r in characters if body.pov in [r.id,r.data.get('entity_id'),r.title,*r.data.get('aliases',[])]),body.pov)
            if pov: entity_set.add(pov)
            associated=or_(*[Record.entity_ids.cast(Text).contains(json.dumps(x,ensure_ascii=False)) for x in entity_set]) if entity_set else Record.id.is_(None)
            scope=or_(Record.kind.in_(['rule','directive','plan']),Record.kind=='knowledge' if not pov else (Record.kind=='knowledge') & (Record.data['character_id'].as_string()==pov),associated, (Record.kind=='foreshadow') & (Record.data['payoff_start'].as_integer()<=c.number))
            active=characters+[r for r in base.filter(Record.kind!='character',scope) if self.active(s,r,t,c.number)]
            constraints=[]; plans=[]; evidence=[]; knowledge=[]
            for r in active:
                item={**dump(r),'reason':'已确认设定'}
                if r.kind=='rule' and r.source_type in ('speech','inference'):
                    evidence.append({**item,'reason':'言论或推断，不能作为硬性世界规则'})
                    continue
                if r.kind=='directive':
                    scope=r.data.get('scope','book'); target=r.data.get('scope_id')
                    matches=scope=='book' or target in [c.id,str(c.number)] or target in p.settings.get('chapter_scopes',{}).get(c.id,[])
                    if matches: constraints.append(item)
                elif r.kind=='rule': constraints.append(item)
                elif r.kind=='plan':
                    if r.data.get('level') in ('book','volume','arc') or r.data.get('scope_id') in [c.id,str(c.number)]: plans.append(item)
                elif r.kind=='knowledge':
                    if not pov or r.data.get('character_id')==pov:
                        knowledge.append({**item,'reason':'场景时间和视角内的人物认知'})
                elif r.kind=='foreshadow' and r.data.get('status','open')=='open':
                    due=r.data.get('payoff_start') is not None and r.data['payoff_start']<=c.number
                    related=bool(set(r.entity_ids)&entity_set)
                    if due or related:
                        evidence.append({**item,'reason':'进入回收窗口' if due else '相关人物或物品再次出现'})
                elif r.kind in ('character','state','relationship','event') and (set(r.entity_ids)&entity_set or r.id in entity_set or r.title in entity_set):
                    evidence.append({**item,'reason':'本章人物或因果关联'})
            # Latest temporal state per entity/property; earlier state retained as evidence only via retrieval.
            latest={}
            for item in evidence:
                if item['kind']=='state':
                    key=(tuple(sorted(item['entity_ids'])),item['data'].get('property',item['title']))
                    if key not in latest or latest[key]['valid_from']<item['valid_from']: latest[key]=item
            evidence=[v for v in evidence if v['kind']!='state']+list(latest.values())
            recent=[]
            for prev in s.query(Chapter).filter(Chapter.project_id==pid,Chapter.branch_id==c.branch_id,Chapter.number<c.number,Chapter.story_time<=t,Chapter.blocked==False,Chapter.confirmed_version_id.is_not(None)).order_by(Chapter.number.desc()).limit(2):
                v=s.get(Version,prev.confirmed_version_id)
                recent.append({'id':prev.id,'kind':'text','title':prev.title,'content':v.content,'source_version_id':v.id,'reason':'最近已确认正文'})
            result={'revision':p.revision,'constraints':constraints,'evidence':[],'character_knowledge':[],'plans':[],'token_estimate':0,'warnings':[],'semantic_search':False,'scene_time':t,'pov':pov,'mode':p.mode,'settings':p.settings}
        base=tokens({'task':body.task,'constraints':constraints})
        if base>body.token_limit: raise HTTPException(409,'硬约束超过上下文预算，请缩小范围或提高模型容量')
        retrieved=self.search(pid,body.task,c.branch_id,t,30,c.number)['items']
        seen=set(); remaining=body.token_limit-base
        for section,items in [('character_knowledge',knowledge),('evidence',evidence),('plans',plans),('evidence',recent),('evidence',retrieved)]:
            for item in items:
                if item['id'] in seen: continue
                size=tokens(item)
                if size>remaining:
                    result['warnings'].append(f'预算不足，未加载：{item["title"]}')
                    continue
                result[section].append(item); seen.add(item['id']); remaining-=size
        result['token_estimate']=body.token_limit-remaining
        return result

    def vector_table(self,provider):
        import lancedb
        import hashlib
        fingerprint=hashlib.sha256(f'{provider["base_url"]}|{provider["embedding_model"]}'.encode()).hexdigest()[:24]
        return lancedb.connect(str(self.data_dir/'vectors'/fingerprint))

    def semantic_results(self,pid,branch,vector,provider,story_time=None,before_number=None,limit=20):
        with self.db.read() as s: require_branch(s,pid,branch)
        conn=self.vector_table(provider)
        if 'evidence' not in conn.list_tables().tables: return []
        table=conn.open_table('evidence')
        candidates=table.search(vector).where(f"project_id = '{pid}' AND branch_id = '{branch}'").limit(limit*4).to_list()
        results=[]
        with self.db.read() as s:
            for x in candidates:
                r=s.get(Record,x['doc_id'])
                if r and self.active(s,r,story_time,before_number) and r.kind not in ('plan','directive') and r.content==x['content']:
                    results.append({**dump(r),'reason':'语义检索，已验证当前证据版本','score':1/(1+x.get('_distance',0))})
                elif not r:
                    c=s.get(Chapter,x['doc_id'])
                    if not c or c.blocked or c.confirmed_version_id!=x['source_version_id']: continue
                    if story_time is not None and c.story_time>story_time: continue
                    if before_number is not None and c.number>=before_number: continue
                    results.append({'id':x['doc_id']+':'+x['source_paragraph_id'],'kind':'text','title':x['title'],'content':x['content'],'source_version_id':x['source_version_id'],'source_paragraph_id':x['source_paragraph_id'],'reason':'语义检索，已验证当前正文版本','score':1/(1+x.get('_distance',0))})
        return results[:limit]
