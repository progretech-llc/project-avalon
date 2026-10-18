#!/usr/bin/env python3
"""Create Avalon-only OpenCode state. Never rewrite global CLI configuration."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import urllib.request


def configure(state, model):
    state = state.resolve()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=5) as r:
        installed = {item['name'] for item in json.load(r)['models']}
    if model not in installed:
        raise ValueError(f'Model is not installed locally: {model}')
    binary = shutil.which('opencode')
    if not binary:
        raise ValueError('OpenCode is not installed')
    for folder in ['workspace','attachments','agent-home/.config/opencode','agent-home/.local/share','agent-home/.cache','agent-home/.local/state']:
        (state/folder).mkdir(parents=True,exist_ok=True,mode=0o700)
    config = {'$schema':'https://opencode.ai/config.json', 'model':f'ollama/{model}',
        'small_model':f'ollama/{model}', 'enabled_providers':['ollama'], 'autoupdate':False,
        'share':'disabled', 'permission':{'*':'deny'}, 'plugin':[],
        'provider':{'ollama':{'npm':'@ai-sdk/openai-compatible','name':'Ollama (local)',
            'options':{'baseURL':'http://127.0.0.1:11434/v1'},
            'models':{model:{'name':model,'limit':{'context':32768,'output':1024}}}}}}
    (state/'agent-home/.config/opencode/opencode.json').write_text(json.dumps(config,indent=2)+'\n')
    (state/'workspace/AGENTS.md').write_text('This isolated workspace is for Avalon foundation checks. Answer text only. Do not use tools.\n')
    path=state/'gateway.json'
    if path.exists():
        gateway=json.loads(path.read_text())
    else:
        gateway={'token':secrets.token_urlsafe(48)}
    gateway.update(binary=binary,model=model)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f:json.dump(gateway,f)
    os.chmod(path,0o600)
    print(f'Configured isolated runtime: {model}; tools denied')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--model',required=True)
    a=p.parse_args();configure(a.state,a.model)
