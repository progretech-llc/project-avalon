"""Wallpaper-only display preferences; conversation history remains in the native store."""
import math
import json

DEFAULTS = dict(enabled=False, placement='anchor-left', opacity=0.72,
                x=0.06, y=0.60, read_aloud=False)


def validate(previous, changes):
    if not isinstance(changes, dict) or set(changes) - DEFAULTS.keys():
        raise ValueError('Unknown wallpaper chat setting')
    candidate = {**previous, **changes}
    for key in ('enabled', 'read_aloud'):
        if type(candidate[key]) is not bool:
            raise ValueError('Choose whether to enable ' + key.replace('_', ' '))
    if candidate['placement'] not in ('anchor-left', 'anchor-right', 'movable'):
        raise ValueError('Choose an anchored or movable chatbox')
    for key, low, high in [('opacity', 0.25, 0.95), ('x', 0, 1), ('y', 0, 1)]:
        value = candidate[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError('Invalid wallpaper chat ' + key)
    return candidate


def latest_exchange(messages):
    """Keep one input/output pair; never pair a new prompt with a previous answer."""
    user = next((m for m in reversed(messages) if m['role'] == 'user'), None)
    reply = next((m for m in reversed(messages) if m['role'] == 'assistant'
                  and user and m['id'] > user['id']), None)
    def public(message):
        if not message:
            return None
        text = message['text']
        snippet = text[:12000]
        while len(json.dumps(snippet)) > 24000:
            snippet = snippet[:len(snippet)//2]
        return dict(id=message['id'], text=snippet + ('…' if len(text) > len(snippet) else ''),
                    status=message['status'])
    return dict(user=public(user), reply=public(reply))
