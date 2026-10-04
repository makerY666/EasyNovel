"""One backend per data directory, regardless of the chosen HTTP port."""
import json
import os
from pathlib import Path


class InstanceBusy(RuntimeError):
    pass


class LocalInstance:
    def __init__(self, directory: Path, metadata: dict):
        self.directory=directory
        self.metadata={**metadata,'pid':os.getpid()}
        self.file=None
        self.marker=directory/'backend-session.json'

    def __enter__(self):
        self.directory.mkdir(parents=True,exist_ok=True)
        self.file=(self.directory/'backend-instance.lock').open('a+b')
        if self.file.seek(0,2)==0:
            self.file.write(b'\0'); self.file.flush()
        self.file.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close(); self.file=None
            raise InstanceBusy('EasyNovel data is already open in another backend.') from exc
        try:
            temporary=self.marker.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.metadata),encoding='utf-8')
            temporary.replace(self.marker)
        except Exception:
            self.__exit__(None,None,None)
            raise
        return self

    def __exit__(self,*_):
        try:
            if self.marker.exists():
                saved=json.loads(self.marker.read_text(encoding='utf-8'))
                if saved==self.metadata: self.marker.unlink(missing_ok=True)
        except (OSError,ValueError):
            pass
        if self.file:
            self.file.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file,fcntl.LOCK_UN)
            self.file.close(); self.file=None
