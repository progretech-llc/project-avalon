#!/usr/bin/env python3
"""Open a board card or delegate an existing Hindsight planet to its native viewer."""
import os
from pathlib import Path
import re
import sys
import webbrowser


def card_url(identifier):
    match = re.fullmatch(r'kanboard-task-([1-9][0-9]{0,9})', identifier)
    if not match:
        raise ValueError('Invalid Kanboard card')
    return 'http://127.0.0.1:18765/?controller=TaskViewController&action=show&task_id='+match[1]+'&project_id=1'


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != '--api':
        raise SystemExit('Expected --api CONFIG PLANET')
    if sys.argv[3].startswith('kanboard-'):
        webbrowser.open(card_url(sys.argv[3]))
    else:
        engine = Path(__file__).resolve().parent.parent / 'pt-constellation-factory-alt-dev/memory_browser.py'
        os.execv(sys.executable, [sys.executable, str(engine), *sys.argv[1:]])
