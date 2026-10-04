import asyncio
import hashlib
import json
import secrets
from contextlib import asynccontextmanager, AsyncExitStack
from pathlib import Path
import aiosqlite
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Body, Query
from fastapi.responses import StreamingResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import func, text
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from . import __version__
from .config import Settings
from .database import Database, Project, Chapter, Version, Record, Branch, Provider, Profile, Run, RunEvent, Call, Job, Impact, dump
from .schemas import ProjectInput, ChapterInput, VersionInput, RecordInput, CommitInput, ContextInput, ProviderInput, ProfileInput, RunInput
from .story import StoryService, require, require_branch, revision, paragraphs_for
from .retrieval import Retrieval
from .gateway import Gateway, Credentials, BudgetExceeded
from .workflow import Workflow
from .storage import Storage, decode_novel, split_novel


def create_app(settings=None,transport=None):
    settings=settings or Settings()
    db=Database(settings.db_path)
    story=StoryService(db); retrieval=Retrieval(db,settings.data_dir); storage=Storage(db,settings)
    credentials=Credentials(settings.test_mode); gateway=Gateway(db,credentials,transport)

    @asynccontextmanager
    async def lifespan(app):
        # Database.initialize snapshots only before a schema migration.
        db.initialize()
        async with AsyncExitStack() as stack:
            saver=await stack.enter_async_context(AsyncSqliteSaver.from_conn_string(str(settings.data_dir/'checkpoints.sqlite3')))
            await saver.setup()
            app.state.saver=saver
            app.state.workflow=Workflow(db,story,retrieval,gateway,saver)
            app.state.background={}
            yield
            await app.state.workflow.shutdown(); await storage.shutdown()
            for task in app.state.background.values():
                if not task.done(): task.cancel()
            await asyncio.gather(*app.state.background.values(),return_exceptions=True)
            if app.state.saver is not saver: await app.state.saver.conn.close()
        db.engine.dispose()

    app=FastAPI(title='EasyNovel',version=__version__,lifespan=lifespan)
    app.state.db=db; app.state.story=story; app.state.gateway=gateway; app.state.credentials=credentials; app.state.settings=settings

    @app.middleware('http')
    async def authenticate(request,call_next):
        supplied=request.headers.get('authorization','')
        if not secrets.compare_digest(supplied,'Bearer '+settings.token):
            return Response(json.dumps({'detail':'本地服务鉴权失败，请重新连接工作台'},ensure_ascii=False),status_code=401,media_type='application/json')
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        return response

    prefix='/api/v1'
    app.add_middleware(CORSMiddleware,allow_origins=['tauri://localhost','http://tauri.localhost','https://tauri.localhost','http://127.0.0.1:5173','http://localhost:5173'],allow_methods=['GET','POST','PATCH','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type'],expose_headers=['Content-Disposition'])

    @app.exception_handler(ValidationError)
    async def model_error(request,exc):
        return JSONResponse({'detail':[{'field':'.'.join(str(x) for x in e['loc']),'message':e['msg']} for e in exc.errors()]},status_code=422)

    @app.exception_handler(KeyError)
    async def missing_field(request,exc):
        return JSONResponse({'detail':'缺少必要字段 '+str(exc.args[0])},status_code=422)

    @app.get(prefix+'/health')
    def health():
        return {'status':'ok','version':__version__,'semantic_search':bool(retrieval.semantic_providers),'legacy_database_detected':settings.legacy_path.exists()}

    @app.post(prefix+'/shutdown')
    async def shutdown():
        await app.state.workflow.shutdown(); await storage.shutdown()
        for task in app.state.background.values():
            if not task.done(): task.cancel()
        callback=getattr(app.state,'shutdown_callback',None)
        if callback: callback()
        return {'ok':True}

    @app.get(prefix+'/projects')
    def projects():
        with db.read() as s: return [dump(p) for p in s.query(Project).order_by(Project.created_at.desc())]

    @app.post(prefix+'/projects')
    def add_project(body:ProjectInput): return story.create_project(body)

    @app.get(prefix+'/projects/{pid}')
    def project(pid:str):
        with db.read() as s: return dump(require(s,Project,pid))

    @app.patch(prefix+'/projects/{pid}')
    def update_project(pid:str,body:dict=Body(...)):
        with db.write() as s:
            p=revision(s,pid,body.get('expected_revision'))
            if 'title' in body and not body['title'].strip(): raise HTTPException(422,'标题不能为空')
            for k in ('title','description','settings'):
                if k in body: setattr(p,k,body[k])
            p.revision+=1; return dump(p)

    @app.get(prefix+'/projects/{pid}/chapters')
    def chapters(pid:str,branch_id:str='main',offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=200)):
        with db.read() as s:
            require(s,Project,pid)
            q=s.query(Chapter).filter_by(project_id=pid,branch_id=branch_id)
            return {'total':q.count(),'items':[dump(c) for c in q.order_by(Chapter.number).offset(offset).limit(limit)]}

    @app.post(prefix+'/projects/{pid}/chapters')
    def chapter_create(pid:str,body:ChapterInput): return story.create_chapter(pid,body)

    @app.get(prefix+'/chapters/{cid}')
    def chapter(cid:str):
        with db.read() as s:
            c=require(s,Chapter,cid)
            return {**dump(c),'draft':dump(s.get(Version,c.draft_version_id)) if c.draft_version_id else None,'confirmed':dump(s.get(Version,c.confirmed_version_id)) if c.confirmed_version_id else None,'project_revision':require(s,Project,c.project_id).revision}

    @app.get(prefix+'/chapters/{cid}/versions')
    def versions(cid:str):
        with db.read() as s:
            require(s,Chapter,cid)
            return [dump(v) for v in s.query(Version).filter_by(chapter_id=cid).order_by(Version.created_at.desc()).limit(200)]

    @app.get(prefix+'/versions/{vid}')
    def version(vid:str):
        with db.read() as s: return dump(require(s,Version,vid))

    @app.post(prefix+'/chapters/{cid}/versions')
    def save(cid:str,body:VersionInput): return story.save_version(cid,body)

    @app.post(prefix+'/chapters/{cid}/commit')
    def commit(cid:str,body:CommitInput): return story.commit(cid,body)

    @app.post(prefix+'/chapters/{cid}/impact')
    def impact(cid:str,body:dict=Body(...)): return story.impact(cid,body['version_id'],body['expected_revision'])

    @app.get(prefix+'/projects/{pid}/impact')
    def impacts(pid:str):
        with db.read() as s:
            require(s,Project,pid)
            return [dump(i) for i in s.query(Impact).filter_by(project_id=pid).order_by(Impact.created_at.desc())]

    @app.post(prefix+'/impact/{iid}/resolve')
    def resolve(iid:str,body:dict=Body(...)): return story.resolve_impact(iid,body)

    @app.post(prefix+'/impact/{iid}/repairs')
    async def repairs(iid:str,body:dict=Body(...)):
        with db.read() as s:
            i=dump(require(s,Impact,iid))
            source=dump(require(s,Version,i['version_id'])) if i['version_id'] else dump(require(s,Record,i['source_record_id']))
        selected=body.get('chapter_ids',[])
        if not selected or not set(selected)<={x['chapter_id'] for x in i['items']}: raise HTTPException(422,'请选择影响范围内的章节')
        if int(body.get('token_budget',0))<=0: raise HTTPException(422,'先配置 token 预算')
        return app.state.workflow.create(i['project_id'],{**body,'task':'修复前文改写造成的后续影响'},'repair',{'source_content':source['content'],'impact':i})

    @app.get(prefix+'/projects/{pid}/records')
    def records(pid:str,kind:str|None=None,branch_id:str='main',status:str|None=None,entity:str|None=None,story_time:float|None=None):
        return story.records(pid,branch_id,kind,status,entity,story_time)

    @app.post(prefix+'/projects/{pid}/records')
    def add_record(pid:str,body:RecordInput): return story.add_record(pid,body)

    @app.patch(prefix+'/records/{rid}')
    def edit_record(rid:str,body:dict=Body(...)): return story.replace_record(rid,dict(body))

    @app.post(prefix+'/records/{rid}/approve')
    def approve_record(rid:str,body:dict=Body(...)): return story.approve_record(rid,body['expected_revision'],body.get('impact_acknowledged',False))

    @app.get(prefix+'/records/{rid}/impact')
    def record_impact(rid:str): return story.record_impact(rid)

    @app.post(prefix+'/records/{rid}/retire')
    def retire_record(rid:str,body:dict=Body(...)):
        with db.write() as s:
            r=require(s,Record,rid); p=revision(s,r.project_id,body['expected_revision'])
            if not body.get('reason','').strip(): raise HTTPException(422,'请填写撤回说明')
            if r.status=='confirmed': story.apply_record_impact(s,r,p,body.get('impact_acknowledged',False))
            r.status='retired'; r.data={**r.data,'retirement_reason':body['reason']}; p.revision+=1
            s.execute(text('DELETE FROM search_fts WHERE doc_id=:id'),{'id':rid})
            return dump(r)

    @app.get(prefix+'/projects/{pid}/search')
    def search(pid:str,q:str='',branch_id:str='main',story_time:float|None=None,limit:int=Query(20,ge=1,le=100)):
        return retrieval.search(pid,q,branch_id,story_time,limit)

    @app.post(prefix+'/projects/{pid}/context')
    def context(pid:str,body:ContextInput): return retrieval.context(pid,body)

    @app.get(prefix+'/projects/{pid}/branches')
    def branches(pid:str):
        with db.read() as s: return [dump(b) for b in s.query(Branch).filter_by(project_id=pid)]

    @app.post(prefix+'/projects/{pid}/branches')
    def fork(pid:str,body:dict=Body(...)):
        if not body.get('name','').strip(): raise HTTPException(422,'请输入分支名')
        return story.fork(pid,body['name'],body.get('source_branch_id','main'))

    @app.post(prefix+'/chapters/{cid}/adopt')
    def adopt(cid:str,body:dict=Body(...)):
        with db.read() as s:
            target=require(s,Chapter,cid); v=require(s,Version,body['source_version_id']); source=require(s,Chapter,v.chapter_id)
            if target.project_id!=source.project_id or target.number!=source.number: raise HTTPException(422,'只能采用同作品同序号章节的版本')
            content=v.content; paragraphs=v.paragraphs
        return story.save_version(cid,VersionInput(content=content,paragraphs=paragraphs,expected_revision=body['expected_revision'],source='manual'))

    @app.post(prefix+'/imports/preview')
    async def preview(file:UploadFile=File(...)):
        if not file.filename or Path(file.filename).suffix.lower() not in ('.txt','.md','.markdown'): raise HTTPException(422,'请选择 TXT 或 Markdown 文件')
        content=await file.read(100*1024*1024+1)
        if len(content)>100*1024*1024: raise HTTPException(413,'文件超过 100MB，请按卷导入')
        decoded,encoding=await asyncio.to_thread(decode_novel,content)
        chapters=await asyncio.to_thread(split_novel,decoded)
        return {'encoding':encoding,'chapters':chapters,'warnings':['未找到章节标题，请手动分章'] if len(chapters)==1 else []}

    @app.post(prefix+'/projects/{pid}/imports')
    async def import_start(pid:str,body:dict=Body(...)): return storage.start_import(pid,body)

    @app.get(prefix+'/projects/{pid}/imports')
    def import_list(pid:str,branch_id:str='main'):
        with db.read() as s:
            require(s,Project,pid); require_branch(s,pid,branch_id)
            jobs=s.query(Job).filter_by(project_id=pid,kind='import').order_by(text('jobs.rowid DESC')).all()
            return [{k:v for k,v in dump(j).items() if k!='payload'} for j in jobs if (j.payload or {}).get('branch_id','main')==branch_id][:100]

    @app.get(prefix+'/imports/{jid}')
    def import_status(jid:str):
        with db.read() as s: return {k:v for k,v in dump(require(s,Job,jid)).items() if k!='payload'}

    @app.post(prefix+'/imports/{jid}/pause')
    def import_pause(jid:str):
        with db.write() as s:
            j=require(s,Job,jid)
            if j.kind!='import' or j.status=='completed': raise HTTPException(409,'已完成的导入任务不能暂停')
            j.status='paused'; return {k:v for k,v in dump(j).items() if k!='payload'}

    @app.post(prefix+'/imports/{jid}/resume')
    async def import_resume(jid:str):
        with db.write() as s:
            j=require(s,Job,jid)
            if j.kind!='import' or j.status=='completed': raise HTTPException(409,'本任务不能继续导入')
            j.status='queued'
        storage.schedule(jid); return import_status(jid)

    @app.post(prefix+'/projects/{pid}/imports/analyze')
    async def analyze(pid:str,body:dict=Body(...)):
        if int(body.get('token_budget',0))<=0: raise HTTPException(422,'先配置 token 预算')
        return app.state.workflow.create(pid,{**body,'task':'分析导入正文，所有自动抽取仅作候选'},'import')

    @app.get(prefix+'/providers')
    def providers():
        with db.read() as s: return [dump(p) for p in s.query(Provider)]

    @app.post(prefix+'/providers')
    def provider_create(body:ProviderInput):
        with db.write() as s:
            p=Provider(**body.model_dump(exclude={'api_key'})); s.add(p); s.flush()
            if body.api_key: credentials.set(p.id,body.api_key); p.has_key=True
            return dump(p)

    @app.patch(prefix+'/providers/{identity}')
    def provider_update(identity:str,body:dict=Body(...)):
        with db.write() as s:
            p=require(s,Provider,identity)
            merged=ProviderInput.model_validate({**dump(p),**body})
            for k,v in merged.model_dump(exclude={'api_key'}).items(): setattr(p,k,v)
            if body.get('api_key') is not None:
                if body['api_key']: credentials.set(p.id,body['api_key']); p.has_key=True
                else: credentials.delete(p.id); p.has_key=False
            return dump(p)

    @app.delete(prefix+'/providers/{identity}')
    def provider_delete(identity:str):
        with db.write() as s:
            p=require(s,Provider,identity)
            if any(r.request.get('provider_id')==identity and r.status not in ('completed','cancelled','failed','stale') for r in s.query(Run)):
                raise HTTPException(409,'模型配置仍被未结束任务使用')
            credentials.delete(identity); s.delete(p)
        return {'ok':True}

    @app.post(prefix+'/providers/{identity}/test')
    async def provider_test(identity:str):
        with db.read() as s: p=dump(require(s,Provider,identity))
        return await gateway.test(p)

    @app.get(prefix+'/profiles')
    def profiles():
        with db.read() as s: return [dump(p) for p in s.query(Profile)]

    @app.post(prefix+'/profiles')
    def profile_create(body:ProfileInput):
        with db.write() as s:
            p=Profile(**body.model_dump()); s.add(p); s.flush(); return dump(p)

    @app.patch(prefix+'/profiles/{identity}')
    def profile_update(identity:str,body:dict=Body(...)):
        with db.write() as s:
            p=require(s,Profile,identity); merged=ProfileInput.model_validate({**dump(p),**body})
            for k,v in merged.model_dump().items(): setattr(p,k,v)
            return dump(p)

    @app.post(prefix+'/projects/{pid}/runs')
    async def run_create(pid:str,body:RunInput): return app.state.workflow.create(pid,body)

    @app.get(prefix+'/projects/{pid}/runs')
    def runs(pid:str):
        with db.read() as s: return [dump(r) for r in s.query(Run).filter_by(project_id=pid).order_by(Run.created_at.desc()).limit(100)]

    @app.get(prefix+'/runs/{rid}')
    def run_get(rid:str): return app.state.workflow.get(rid)

    @app.get(prefix+'/runs/{rid}/calls')
    def calls(rid:str):
        with db.read() as s:
            require(s,Run,rid); return [dump(c) for c in s.query(Call).filter_by(run_id=rid)]

    @app.post(prefix+'/runs/{rid}/approve-plan')
    async def approve_plan(rid:str,body:dict=Body(default={})):
        r=run_get(rid)
        if r['status']!='awaiting_plan': raise HTTPException(409,'任务不在计划审核阶段')
        await app.state.workflow.settle(rid)
        app.state.workflow.update(rid,status='running')
        app.state.workflow.schedule(rid,Command(resume={'plan_index':0,**body})); return run_get(rid)

    @app.post(prefix+'/runs/{rid}/approve')
    async def approve(rid:str,body:dict=Body(...)):
        r=run_get(rid)
        if r['status']!='awaiting_review': raise HTTPException(409,'任务不在正文审核阶段')
        if body.get('expected_revision')!=r['input_revision']: raise HTTPException(409,'请重新审核过期任务')
        if not body.get('idempotency_key'): raise HTTPException(422,'需要幂等提交键')
        issues=[x for review in r['artifacts'].get('reviews',[]) for x in review['issues'] if x['severity']=='critical']
        if issues and not body.get('override_reason','').strip(): raise HTTPException(409,'关键问题未解决，请修改或填写作者确认说明')
        indices=body.get('accepted_memory_indices',[])
        if any(not isinstance(i,int) or i<0 or i>=len(r['artifacts'].get('memory_delta',[])) for i in indices): raise HTTPException(422,'选择的记忆不存在')
        await app.state.workflow.settle(rid)
        app.state.workflow.update(rid,status='running')
        app.state.workflow.schedule(rid,Command(resume=body)); return run_get(rid)

    @app.post(prefix+'/runs/{rid}/pause')
    async def run_pause(rid:str):
        r=run_get(rid)
        if r['status']=='completed': raise HTTPException(409,'任务已完成')
        app.state.workflow.update(rid,status='paused')
        task=app.state.workflow.tasks.get(rid)
        if task and not task.done(): task.cancel(); await asyncio.gather(task,return_exceptions=True)
        return run_get(rid)

    @app.post(prefix+'/runs/{rid}/revise')
    async def revise_from_author(rid:str,body:dict=Body(...)):
        r=run_get(rid)
        instruction=body.get('instruction','')
        if not isinstance(instruction,str) or not instruction.strip() or len(instruction)>50000: raise HTTPException(422,'请填写有效修改要求')
        if not r['chapter_id'] or r['status'] not in ('awaiting_review','completed','stale') or not r['artifacts'].get('version_id'): raise HTTPException(409,'请先完成正文生成再提出修改')
        with db.read() as s: revision(s,r['project_id'],body.get('expected_revision'))
        await app.state.workflow.settle(rid)
        request={key:r['request'][key] for key in ('chapter_id','provider_id','token_budget','money_budget','profile_id','pov','entities','story_time') if key in r['request']}
        original_task=r['request'].get('original_task') or r['request'].get('task','').split('\n作者本次修改要求：',1)[0]
        request['task']=original_task+'\n作者本次修改要求：'+instruction.strip()
        return app.state.workflow.create(r['project_id'],RunInput.model_validate(request),kind='author_revision',extra={'version_id':r['artifacts']['version_id'],'parent_run_id':rid,'expected_revision':body['expected_revision'],'original_task':original_task,'revision_instruction':instruction.strip(),'approved_plan':r['artifacts'].get('plan'),'profile_snapshot':r['request']['profile_snapshot'],'provider_snapshots':r['request']['provider_snapshots']})

    @app.post(prefix+'/runs/{rid}/resume')
    async def run_resume(rid:str,body:dict=Body(default={})):
        r=run_get(rid)
        if r['status'] not in ('paused','failed'): raise HTTPException(409,'任务不能恢复')
        if body:
            with db.write() as s:
                obj=require(s,Run,rid); values=dict(obj.request)
                if 'token_budget' in body and int(body['token_budget'])>0: values['token_budget']=int(body['token_budget'])
                if 'money_budget' in body: values['money_budget']=body['money_budget']
                if 'provider_output_limits' in body:
                    snapshots=json.loads(json.dumps(values.get('provider_snapshots',{})))
                    limits=body['provider_output_limits']
                    if not isinstance(limits,dict): raise HTTPException(422,'模型输出上限无效')
                    for identity,limit in limits.items():
                        if identity not in snapshots or type(limit) is not int or limit<128 or limit>100000 or limit>=snapshots[identity]['context_limit']:
                            raise HTTPException(422,'模型输出上限无效，须小于模型上下文容量')
                        snapshots[identity]['max_output']=limit
                    values['provider_snapshots']=snapshots
                if 'role_limits' in body:
                    snapshot=json.loads(json.dumps(values.get('profile_snapshot',{})))
                    roles=snapshot.setdefault('roles',{})
                    for role,limit in body['role_limits'].items():
                        if role not in ('architect','planner','writer','continuity','editor','stylist','memory') or not isinstance(limit,int) or limit<128 or limit>100000:
                            raise HTTPException(422,'角色输出上限无效')
                        roles.setdefault(role,{})['max_output']=limit
                    values['profile_snapshot']=snapshot
                obj.request=values
        app.state.workflow.update(rid,status='running',error=None)
        if r['request'].get('kind') in ('chapter','rewrite','author_revision'):
            graph=app.state.workflow.revision_graph if r['request'].get('kind')=='author_revision' else app.state.workflow.graph
            checkpoint=await graph.aget_state({'configurable':{'thread_id':rid}})
            input_value=None if checkpoint.values else {'run_id':rid}
        else: input_value=None
        app.state.workflow.schedule(rid,input_value); return run_get(rid)

    @app.post(prefix+'/runs/{rid}/cancel')
    async def cancel(rid:str):
        run_get(rid); app.state.workflow.update(rid,status='cancelled',node='cancelled')
        task=app.state.workflow.tasks.get(rid)
        if task and not task.done(): task.cancel(); await asyncio.gather(task,return_exceptions=True)
        return run_get(rid)

    @app.post(prefix+'/runs/{rid}/edit')
    async def edit_run(rid:str,body:dict=Body(...)):
        r=run_get(rid)
        if r['status']!='awaiting_review': raise HTTPException(409,'只能修改待审核正文')
        await app.state.workflow.settle(rid)
        content=body.get('draft','')
        if not content.strip(): raise HTTPException(422,'正文不能为空')
        from .story import preserve_locks,verify_paragraphs
        paragraphs=body.get('paragraphs') or paragraphs_for(content,r['artifacts']['paragraphs'])
        verify_paragraphs(content,paragraphs); preserve_locks(r['artifacts']['paragraphs'],paragraphs)
        app.state.workflow.artifact(rid,draft=content,paragraphs=paragraphs)
        async def reaudit():
            try:
                app.state.workflow.check(rid,'manual_reaudit')
                await app.state.workflow.audits(rid,'manual:'+hashlib.sha256(content.encode()).hexdigest()[:16])
                await app.state.workflow.memory({'run_id':rid})
                app.state.workflow.update(rid,status='awaiting_review',node='review')
            except asyncio.CancelledError:
                if run_get(rid)['status']!='cancelled': app.state.workflow.update(rid,status='paused',error='修改稿审核已暂停，成果保留')
            except BudgetExceeded as exc: app.state.workflow.update(rid,status='paused',error=str(exc))
            except HTTPException as exc: app.state.workflow.update(rid,status='stale' if exc.status_code==409 else 'failed',error=str(exc.detail))
            except Exception as exc: app.state.workflow.update(rid,status='failed',error='修改稿审核失败，成果保留')
        app.state.workflow.update(rid,status='running')
        app.state.workflow.tasks[rid]=asyncio.create_task(reaudit())
        return run_get(rid)

    @app.get(prefix+'/runs/{rid}/events')
    async def events(rid:str,request:Request,after:int=Query(0,ge=0)):
        run_get(rid)
        async def stream():
            cursor=after; quiet=0
            while not await request.is_disconnected():
                with db.read() as s:
                    rows=[dump(e) for e in s.query(RunEvent).filter(RunEvent.run_id==rid,RunEvent.seq>cursor).order_by(RunEvent.seq).limit(200)]
                    status=require(s,Run,rid).status
                for e in rows:
                    cursor=e['seq']; yield f'id: {cursor}\nevent: {e["event"]}\ndata: '+json.dumps({'seq':cursor,'event':e['event'],'data':e['data']},ensure_ascii=False)+'\n\n'
                if not rows:
                    if status not in ('running','queued'): break
                    quiet+=1
                    if quiet%20==0: yield ': heartbeat\n\n'
                    await asyncio.sleep(0.25)
        return StreamingResponse(stream(),media_type='text/event-stream')

    @app.post(prefix+'/projects/{pid}/directives/parse')
    async def parse(pid:str,body:dict=Body(...)):
        if not body.get('text','').strip() or int(body.get('token_budget',0))<=0: raise HTTPException(422,'需要指令与 token 预算')
        return app.state.workflow.create(pid,{**body,'task':body['text']},'directive')

    @app.post(prefix+'/chapters/{cid}/rewrite')
    async def rewrite(cid:str,body:dict=Body(...)):
        with db.read() as s:
            c=require(s,Chapter,cid); revision(s,c.project_id,body['expected_revision']); v=require(s,Version,body['version_id'])
            if v.chapter_id!=cid: raise HTTPException(422,'版本属于其他章节')
            selected=set(body.get('paragraph_ids',[])); allowed={p['id'] for p in v.paragraphs if not p.get('locked')}
            if not selected or not selected<=allowed: raise HTTPException(422,'请选择存在且未锁定的段落')
            pid=c.project_id
        request=RunInput.model_validate({**body,'chapter_id':cid,'task':body['instruction']})
        return app.state.workflow.create(pid,request,'rewrite',{'version_id':body['version_id'],'paragraph_ids':list(selected)})

    @app.post(prefix+'/backups')
    async def backup(body:dict=Body(default={})):
        if any(not t.done() for t in app.state.workflow.tasks.values()) or any(not t.done() for t in storage.tasks.values()):
            raise HTTPException(409,'请先暂停运行任务，再创建完整备份')
        return await asyncio.to_thread(storage.backup,body.get('automatic',False))

    @app.get(prefix+'/backups')
    def backups(): return storage.backups()

    @app.get(prefix+'/backups/{identity}/download')
    def download(identity:str):
        path=storage.backup_path(identity); return FileResponse(path,filename=path.name,media_type='application/zip')

    @app.post(prefix+'/backups/{identity}/restore')
    async def restore(identity:str,body:dict=Body(...)):
        if body.get('confirmation')!='RESTORE': raise HTTPException(422,'需要确认恢复范围')
        if any(not t.done() for t in app.state.workflow.tasks.values()) or any(not t.done() for t in storage.tasks.values()) or any(not t.done() for t in app.state.background.values()): raise HTTPException(409,'请先暂停所有任务')
        storage.backup(automatic=True)
        await app.state.saver.conn.close()
        try: result=storage.restore(identity)
        finally:
            conn=await aiosqlite.connect(str(settings.data_dir/'checkpoints.sqlite3'))
            saver=AsyncSqliteSaver(conn); await saver.setup(); app.state.saver=saver
            app.state.workflow=Workflow(db,story,retrieval,gateway,saver)
        return result

    @app.post(prefix+'/legacy/import')
    async def legacy(): return await asyncio.to_thread(storage.import_legacy)

    @app.get(prefix+'/projects/{pid}/export')
    def export(pid:str,format:str='txt',branch_id:str='main'):
        if format not in ('txt','md'): raise HTTPException(422,'仅支持 txt 或 md')
        with db.read() as s:
            p=require(s,Project,pid); chunks=[]
            for c in s.query(Chapter).filter_by(project_id=pid,branch_id=branch_id).filter(Chapter.confirmed_version_id.is_not(None)).order_by(Chapter.number):
                chunks.append(('## ' if format=='md' else '')+c.title+'\n\n'+require(s,Version,c.confirmed_version_id).content)
            content='\n\n'.join(chunks)
        from urllib.parse import quote
        return Response(content,media_type='text/plain; charset=utf-8',headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(p.title+'.'+format)})

    @app.post(prefix+'/projects/{pid}/index')
    async def create_index(pid:str,body:dict=Body(...)):
        if int(body.get('token_budget',0))<=0: raise HTTPException(422,'嵌入索引需要显式 token 预算')
        with db.write() as s:
            p=require(s,Project,pid); provider=dump(require(s,Provider,body['provider_id']))
            require_branch(s,pid,body.get('branch_id','main'))
            if not provider.get('embedding_model'): raise HTTPException(422,'请先配置嵌入模型')
            records=[dump(r) for r in s.query(Record).filter_by(project_id=pid,branch_id=body.get('branch_id','main'),status='confirmed') if retrieval.active(s,r) and r.kind not in ('plan','directive')]
            docs=[{'doc_id':r['id'],'project_id':pid,'branch_id':r['branch_id'],'source_version_id':r['source_version_id'] or '', 'source_paragraph_id':r['source_paragraph_id'] or '', 'title':r['title'],'content':r['content']} for r in records]
            for c in s.query(Chapter).filter_by(project_id=pid,branch_id=body.get('branch_id','main'),blocked=False).filter(Chapter.confirmed_version_id.is_not(None)):
                v=require(s,Version,c.confirmed_version_id)
                for block in v.paragraphs:
                    if block['text'].strip(): docs.append({'doc_id':c.id,'project_id':pid,'branch_id':c.branch_id,'source_version_id':v.id,'source_paragraph_id':block['id'],'title':c.title,'content':block['text']})
            r=Run(project_id=pid,input_revision=p.revision,request={'kind':'index','provider_id':provider['id'],'token_budget':body['token_budget'],'money_budget':body.get('money_budget'),'provider_snapshots':{provider['id']:provider},'project_token_budget':p.settings.get('token_budget'),'project_money_budget':p.settings.get('money_budget')},node='index')
            s.add(r); s.flush(); j=Job(project_id=pid,kind='index',total=len(docs),payload={'run_id':r.id,'branch_id':body.get('branch_id','main')}); s.add(j); s.flush(); jid=j.id; rid=r.id
        async def build_index():
            try:
                with db.write() as s: require(s,Run,rid).status='running'; require(s,Job,jid).status='running'
                conn=await asyncio.to_thread(retrieval.vector_table,provider)
                table=None
                for offset in range(0,len(docs),16):
                    batch=docs[offset:offset+16]
                    vectors=await gateway.embeddings(rid,'index:'+str(offset),[d['content'] for d in batch],provider)
                    data=[{**d,'vector':v} for d,v in zip(batch,vectors)]
                    if table is None:
                        existing='evidence' in (await asyncio.to_thread(conn.list_tables)).tables
                        if existing:
                            table=await asyncio.to_thread(conn.open_table,'evidence')
                            await asyncio.to_thread(table.delete,f"project_id = '{pid}' AND branch_id = '{body.get('branch_id','main')}'")
                            await asyncio.to_thread(table.add,data)
                        else: table=await asyncio.to_thread(conn.create_table,'evidence',data)
                    else: await asyncio.to_thread(table.add,data)
                    with db.write() as s: require(s,Job,jid).completed=offset+len(batch)
                retrieval.register(pid,body.get('branch_id','main'),provider)
                with db.write() as s: require(s,Job,jid).status='completed'; require(s,Run,rid).status='completed'
            except asyncio.CancelledError:
                with db.write() as s: require(s,Job,jid).status='paused'; require(s,Run,rid).status='paused'
            except Exception as exc:
                with db.write() as s: require(s,Job,jid).status='failed'; require(s,Job,jid).error='索引构建未完成，请检查预算与嵌入服务'; require(s,Run,rid).status='failed'
        app.state.background[jid]=asyncio.create_task(build_index()); return {'id':jid,'status':'queued'}

    @app.get(prefix+'/index/{jid}')
    def index_status(jid:str): return import_status(jid)

    @app.post(prefix+'/projects/{pid}/search')
    async def semantic_search(pid:str,body:dict=Body(...)):
        q=body.get('q',''); branch=body.get('branch_id','main'); provider=retrieval.semantic_providers.get((pid,branch))
        if not provider: raise HTTPException(409,'本分支还没有可用语义索引')
        if int(body.get('token_budget',0))<=0: raise HTTPException(422,'查询嵌入需要 token 预算')
        with db.write() as s:
            p=require(s,Project,pid); r=Run(project_id=pid,input_revision=p.revision,status='running',node='search',request={'kind':'search','provider_id':provider['id'],'token_budget':body['token_budget'],'provider_snapshots':{provider['id']:provider},'project_token_budget':p.settings.get('token_budget'),'project_money_budget':p.settings.get('money_budget')})
            s.add(r); s.flush(); rid=r.id
        try:
            vector=(await gateway.embeddings(rid,'query',[q],provider))[0]
            result=retrieval.search(pid,q,branch,body.get('story_time'))
            semantic=await asyncio.to_thread(retrieval.semantic_results,pid,branch,vector,provider,body.get('story_time'))
            seen={x['id'] for x in result['items']}
            result['items']+= [x for x in semantic if x['id'] not in seen]
            result['semantic_search']=True
            with db.write() as s: require(s,Run,rid).status='completed'
            return result
        except Exception:
            with db.write() as s: require(s,Run,rid).status='failed'
            raise HTTPException(502,'语义查询失败，仍可使用全文检索')

    return app
