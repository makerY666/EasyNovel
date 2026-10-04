import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
import uvicorn
from .config import Settings
from .app import create_app
from .instance import LocalInstance, InstanceBusy


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--data-dir',type=Path)
    parser.add_argument('--parent-pid',type=int)
    args=parser.parse_args(); settings=Settings(port=args.port)
    if args.data_dir: settings.data_dir=args.data_dir
    # Child-process stdout bootstrap consumed by desktop; never output provider API keys.
    print(json.dumps({'base_url':f'http://127.0.0.1:{settings.port}','token':settings.token}),flush=True)
    app=create_app(settings)
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=settings.port,log_level='warning',access_log=False))
    app.state.shutdown_callback=lambda:setattr(server,'should_exit',True)
    async def serve():
        async def watch_parent():
            while not server.should_exit:
                if not parent_alive(args.parent_pid):
                    server.should_exit=True
                    return
                await asyncio.sleep(1)
        watcher=asyncio.create_task(watch_parent()) if args.parent_pid else None
        try: await server.serve()
        finally:
            if watcher:
                watcher.cancel()
                await asyncio.gather(watcher,return_exceptions=True)
    try:
        with LocalInstance(settings.data_dir,{'port':settings.port,'token':settings.token}):
            asyncio.run(serve())
    except InstanceBusy as exc:
        print(str(exc),file=sys.stderr)
        raise SystemExit(2) from exc


def parent_alive(pid):
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.OpenProcess(0x100000,False,pid)
        if not handle: return False
        try: return kernel.WaitForSingleObject(handle,0)==258
        finally: kernel.CloseHandle(handle)
    try: os.kill(pid,0); return True
    except ProcessLookupError: return False
    except PermissionError: return True


if __name__=='__main__': main()
