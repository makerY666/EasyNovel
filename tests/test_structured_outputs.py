import json
from unittest.mock import patch
import httpx
import pytest
from easynovel.gateway import parse_structured_output,StructuredOutputError
from easynovel.schemas import MemoryOutput,DraftOutput
from conftest import project,chapter,provider,wait_run
from test_generation_limits import run_body


def test_single_json_with_fence_and_explanation_is_validated():
    output='```json\n{"records":[]}\n```\n修复说明：kind 应为 event，source_type 为 speech。'
    assert parse_structured_output(output,MemoryOutput).records==[]
    with pytest.raises(ValueError): parse_structured_output('{"records":[]}\n说明\n{"records":[{}]}',MemoryOutput)
    with pytest.raises(ValueError): parse_structured_output('{"records":[]}\ntrue',MemoryOutput)
    with pytest.raises(ValueError): parse_structured_output('{"records":[{"kind":"speech"}]}\n说明',MemoryOutput)


def test_saved_invalid_response_and_repair_are_reused_without_more_calls(studio):
    c,app,fixture=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    original=fixture.__class__.__call__
    def annotated_repair(self,request):
        response=original(self,request); data=response.json()
        prompt=json.loads(request.content)['messages'][-1]['content']
        if '只修复以下 JSON' in prompt:
            output={'records':[{'kind':'event','title':'言论','content':'林舟说话','quote':'林舟拾起玉佩。','source_type':'speech'}]}
            data['choices'][0]['message']['content']=json.dumps(output,ensure_ascii=False)+'\n修复说明：言论用 event/speech。'
        elif '"title": "MemoryOutput"' in prompt:
            data['choices'][0]['message']['content']=json.dumps({'records':[{'kind':'speech','title':'言论','content':'林舟说话','quote':'林舟拾起玉佩。','source_type':'speech'}]},ensure_ascii=False)
        return httpx.Response(200,json=data)
    with patch.object(fixture.__class__,'__call__',annotated_repair):
        run=c.post(f'/api/v1/projects/{p["id"]}/runs',json=run_body(ch,model,auto_approve_plan=True)).json()
        result=wait_run(c,run['id'],['awaiting_review','failed','paused'])
    assert result['status']=='awaiting_review',result
    assert result['artifacts']['memory_delta'][0]['source_type']=='speech'
    prior=len(fixture.requests)
    # Re-run only the node with its same head. Both paid outputs are already cached.
    import asyncio
    asyncio.run(app.state.workflow.memory({'run_id':run['id']}))
    assert len(fixture.requests)==prior


def test_invalid_memory_warns_without_losing_reviewable_prose(studio):
    c,_,fixture=studio; p=project(c); ch=chapter(c,p['id']); model=provider(c)
    original=fixture.__class__.__call__
    def malformed_memory(self,request):
        response=original(self,request); data=response.json()
        prompt=json.loads(request.content)['messages'][-1]['content']
        if '"title": "MemoryOutput"' in prompt:
            data['choices'][0]['message']['content']='{"records":[{"kind":"not-a-kind"}]}'
        return httpx.Response(200,json=data)
    with patch.object(fixture.__class__,'__call__',malformed_memory):
        run=c.post(f'/api/v1/projects/{p["id"]}/runs',json=run_body(ch,model,auto_approve_plan=True)).json()
        result=wait_run(c,run['id'],['awaiting_review','failed','paused'])
    assert result['status']=='awaiting_review',result
    assert result['artifacts']['draft'] and result['artifacts']['version_id']
    assert result['artifacts']['memory_delta']==[]
    assert result['artifacts']['memory_warnings'][0]['paragraph_ids']
    assert 'records.0.kind' in result['artifacts']['memory_warnings'][0]['message']
    assert sum('"title": "MemoryOutput"' in json.loads(q.content)['messages'][-1]['content'] for q in fixture.requests)==2
