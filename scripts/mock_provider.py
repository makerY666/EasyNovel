"""Local deterministic provider for UI acceptance; no external model calls."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
import httpx
import uvicorn
from fastapi import FastAPI,Request
from fastapi.responses import Response
from conftest import ModelFixture

app=FastAPI(); fixture=ModelFixture()

@app.post('/v1/chat/completions')
async def completion(request:Request):
    result=fixture(httpx.Request('POST','https://fixture.invalid/v1/chat/completions',content=await request.body()))
    return Response(content=result.content,media_type='application/json')

if __name__=='__main__': uvicorn.run(app,host='127.0.0.1',port=8788,access_log=False,log_level='warning')
