"""Confirmed recipient rules for weekly technology reports."""
import re
from collections import defaultdict

RECIPIENTS = {
    'lwr': 'Languages, Literatures and Cultures',
    'visu': 'Visual Studies',
    'performing': 'Performing Arts',
}
DEPARTMENTS = {'LWR': 'lwr', 'VISU': 'visu', 'GDES': 'visu', 'VGAM': 'visu',
               'ANIM': 'visu', 'THAR': 'performing', 'MUSI': 'performing'}


def field(item, name):
    prefix = name + ': '
    return next((line[len(prefix):].strip() for line in (item.get('notes') or '').splitlines()
                 if line.startswith(prefix)), '')


def title_key(title):
    return ' '.join(str(title or '').casefold().split())


def recipient(title, department='', room=''):
    context = f'{title} {room}'
    if re.search(r'\b(?:HCH\s*|Holy Cross(?: Hall)?\s+)(?:203|326)\b|\bHUMX4\b|cards?\s*wipe|card access|\b24.?hour access\b|\bA120tsm\b.*\breplacement\b|\b(?:replace|replacement)\b.*\b(?:A120|120,?\s+113)', context, re.I):
        return 'dean'
    if re.search(r'\b(?:ARTS?\s*140|A140)(?=\b|[A-Z]\d)|\bTHAR\s+C7000\b|\b(?:Music printer|East Hall\s+140|EH\s*140)\b', context, re.I):
        return 'performing'
    if re.search(r'\b(?:Sorin(?: Hall)?|HUMX2)\b', context, re.I):
        return 'lwr'
    if re.search(r'\b(?:Flextight|Imacon|Ali Rex|Visual Print Lab|VPL|ARTS?\s*133|A133)\b', context, re.I):
        return 'visu'
    if department.strip():
        return DEPARTMENTS.get(department.strip().upper())
    if re.search(r'\b(?:ARTS?\s*121|A121|TH\s*108|Trustee(?: Hall)?\s+108|LIB(?:RARY)?\s*115|LIB(?:RARY)?\s*127|MOOD(?:Y(?: Hall)?)?\s*301|MH301)(?=\b|(?:M\d|tsm))|\b(?:Animation|P7570)\b', context, re.I):
        return 'visu'
    return None


def task_routes(tasks, sheet_rows):
    tags = defaultdict(set)
    for item in sheet_rows:
        if department := field(item, 'Department'):
            tags[title_key(item.get('title'))].add(department)
    routes = {}
    for task in tasks:
        title = task.get('title') or ''
        candidates = tags.get(title_key(title), set())
        if len(candidates) > 1:
            resolved = {DEPARTMENTS.get(tag.upper()) for tag in candidates}
            if len(resolved) != 1:
                continue
        department = next(iter(candidates), '')
        routes[str(task['id'])] = recipient(title, department)
    return routes
