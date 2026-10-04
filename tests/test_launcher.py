import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
import pytest
from easynovel.instance import InstanceBusy,LocalInstance

ROOT=Path(__file__).resolve().parents[1]


def test_backend_data_lock_and_metadata_cleanup(tmp_path):
    marker=tmp_path/'backend-session.json'
    with LocalInstance(tmp_path,{'port':8765,'token':'local-test'}):
        assert json.loads(marker.read_text())['port']==8765
        with pytest.raises(InstanceBusy):
            with LocalInstance(tmp_path,{'port':8766,'token':'second'}): pass
        assert json.loads(marker.read_text())['token']=='local-test'
    assert not marker.exists()
    with LocalInstance(tmp_path,{'port':8766,'token':'restart'}): pass
    assert not marker.exists()


def wait_session(directory,process,other=None):
    marker=directory/'browser-session.json'
    until=time.monotonic()+45
    while time.monotonic()<until:
        if process.poll() is not None and (other is None or other.poll() is not None):
            out,err=process.communicate()
            raise AssertionError(f'launcher exited early: {out}\n{err}')
        try:
            session=json.loads(marker.read_text(encoding='utf-8-sig'))
            with httpx.Client(trust_env=False,timeout=1) as client:
                response=client.get(f'http://127.0.0.1:{session["web_port"]}/api/v1/health',headers={'Authorization':'Bearer '+session['token']})
                if response.status_code==200 and response.json()['status']=='ok': return session
        except (OSError,ValueError,httpx.HTTPError): pass
        time.sleep(.1)
    raise AssertionError('launcher did not become ready')


def command(backend,web):
    return ['powershell.exe','-NoProfile','-File',str(ROOT/'scripts/start-browser.ps1'),'-Port',str(backend),'-WebPort',str(web)]


def shutdown(session):
    with httpx.Client(trust_env=False,timeout=5) as client:
        client.post(f'http://127.0.0.1:{session["port"]}/api/v1/shutdown',headers={'Authorization':'Bearer '+session['token']}).raise_for_status()


@pytest.mark.skipif(sys.platform!='win32',reason='Windows launcher integration')
def test_occupied_ports_double_click_and_restart(tmp_path):
    # Hold both requested ports without running any EasyNovel service on them.
    with socket.socket() as occupied_backend,socket.socket() as occupied_web:
        occupied_backend.bind(('127.0.0.1',0)); occupied_backend.listen()
        occupied_web.bind(('127.0.0.1',0)); occupied_web.listen()
        backend=occupied_backend.getsockname()[1]; web=occupied_web.getsockname()[1]
        directory=tmp_path/'中文 路径'
        env={**os.environ,'EASYNOVEL_DATA_DIR':str(directory)}
        flags=subprocess.CREATE_NO_WINDOW
        first=subprocess.Popen(command(backend,web),cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=flags)
        second=None; session=None
        try:
            # Simulate two clicks before the first launch has finished.
            second=subprocess.Popen(command(backend,web),cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=flags)
            session=wait_session(directory,first,second)
            if session['launcher_pid']==second.pid:
                first,second=second,first
            assert session['launcher_pid']==first.pid
            assert session['port']!=backend and session['web_port']!=web
            out,err=second.communicate(timeout=45)
            assert second.returncode==0,(out,err)
            assert 'already running' in out
            after=json.loads((directory/'browser-session.json').read_text(encoding='utf-8-sig'))
            assert after==session
            # Reusing an existing instance is independent of requested/default ports.
            again=subprocess.run(command(8765,5173),cwd=ROOT,env=env,capture_output=True,text=True,timeout=10,creationflags=flags)
            assert again.returncode==0 and 'already running' in again.stdout
            shutdown(session)
            out,err=first.communicate(timeout=15)
            assert first.returncode==0,(out,err)
            assert 'stopped safely' in out
            assert not (directory/'browser-session.json').exists()
            assert not (directory/'backend-session.json').exists()
            session=None
            # A normal next start obtains a fresh token and leaves saved data in place.
            first=subprocess.Popen(command(backend,web),cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=flags)
            session=wait_session(directory,first)
            assert session['token']!=after['token']
            assert (directory/'studio.sqlite3').exists()
            shutdown(session)
            first.communicate(timeout=15)
            assert first.returncode==0
        finally:
            if session and first.poll() is None:
                try: shutdown(session)
                except httpx.HTTPError: pass
            for proc in (first,second):
                if proc and proc.poll() is None:
                    try: proc.wait(timeout=10)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)


@pytest.mark.skipif(sys.platform!='win32',reason='Windows launcher integration')
def test_manually_started_backend_is_reused(tmp_path):
    with socket.socket() as free:
        free.bind(('127.0.0.1',0)); port=free.getsockname()[1]
    env={**os.environ,'EASYNOVEL_DATA_DIR':str(tmp_path),'EASYNOVEL_TOKEN':'manual-local-test'}
    flags=subprocess.CREATE_NO_WINDOW
    backend=subprocess.Popen([sys.executable,'-m','easynovel','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=flags)
    launcher=None; session=None
    try:
        until=time.monotonic()+30
        while time.monotonic()<until:
            try:
                with httpx.Client(trust_env=False,timeout=1) as client:
                    if client.get(f'http://127.0.0.1:{port}/api/v1/health',headers={'Authorization':'Bearer manual-local-test'}).status_code==200: break
            except httpx.HTTPError: pass
            time.sleep(.1)
        else: raise AssertionError('manual backend did not start')
        metadata=json.loads((tmp_path/'backend-session.json').read_text())
        launcher=subprocess.Popen(command(8765,5173),cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=flags)
        session=wait_session(tmp_path,launcher)
        assert session['port']==port and session['pid']==metadata['pid']
        assert session['token']=='manual-local-test'
        shutdown(session)
        backend.communicate(timeout=15)
        out,err=launcher.communicate(timeout=15)
        assert backend.returncode==0 and launcher.returncode==0,(out,err)
        assert not (tmp_path/'backend-session.json').exists()
    finally:
        if backend.poll() is None:
            try: shutdown({'port':port,'token':'manual-local-test'})
            except httpx.HTTPError: pass
        for proc in (launcher,backend):
            if proc and proc.poll() is None:
                try: proc.wait(timeout=10)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)
