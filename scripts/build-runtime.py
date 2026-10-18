#!/usr/bin/env python3
"""Fetch pinned upstream sources/toolchain and build only Avalon's runtime host."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]

def run(*argv,cwd=ROOT):
    subprocess.run(argv,cwd=cwd,check=True)

def main():
    pin=json.loads((ROOT/'dependencies.json').read_text())
    source=ROOT/'.deps/lampos'; tools=ROOT/'.tools'
    tools.mkdir(exist_ok=True);source.parent.mkdir(exist_ok=True)
    if not source.exists():
        run('git','clone','--filter=blob:none','--no-checkout',pin['lampos']['repository'],str(source))
    head=subprocess.run(['git','rev-parse','HEAD'],cwd=source,capture_output=True,text=True)
    if head.stdout.strip()!=pin['lampos']['revision']:
        dirty=subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True)
        if dirty.strip():raise RuntimeError('Pinned LampOS checkout has local work; refusing to overwrite it')
        run('git','fetch','--depth=1','origin',pin['lampos']['revision'],cwd=source)
        run('git','checkout','--detach',pin['lampos']['revision'],cwd=source)
    run('git','diff','--exit-code',cwd=source)
    run('git','diff','--cached','--exit-code',cwd=source)
    go=tools/'go/bin/go'
    if not go.exists():
        if __import__('platform').machine()!='x86_64':raise RuntimeError('This foundation build is qualified for Linux x86_64 only')
        archive=tools/'go.tar.gz'
        urllib.request.urlretrieve(f"https://go.dev/dl/go{pin['go']['version']}.linux-amd64.tar.gz",archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=pin['go']['linux_amd64_sha256']:
            raise RuntimeError('Go archive checksum mismatch')
        with tarfile.open(archive) as t:t.extractall(tools,filter='data')
        archive.unlink()
    run(str(go),'mod','verify')
    for name in ['avalon-runtime','avalon-probe','avalon-harness-link']:
        run(str(go),'build','-mod=readonly','-o',str(tools/name),'./cmd/'+name)
    run(str(go),'build','-mod=readonly','-o',str(tools/'lampos-os-server'),'go.autonomous.ai/os/system/cmd/os-server')
    print('Built pinned LampOS host and probe. No user services or agent settings changed.')

if __name__=='__main__':main()
