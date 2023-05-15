import re
import subprocess
from collections import namedtuple


ISSUE_REGEX = re.compile(r'\b[A-Za-z]{2,4}-\d+\b')
ISSUE_BLACKLIST = (
    "RS-232",
    "UTF-8",
    "UTF-16",
)

COMMITTYPES = {
    'feature': '(+)',
    'bugfix': '(x)',
    'refactoring': '(*)',
    'internal': '(i)',
    'release': '(flag)',
    'next-version-start': '(flagoff)'}
SUBJECT_REGEX = re.compile(rf'^\[({"|".join(COMMITTYPES)})] (.*)')

Commit = namedtuple('Commit', 'commitid, author, subject, body')
Subject = namedtuple('subject', 'is_valid symbol text')


def parse_issues(text):
    unique_issues = set(map(str.upper, ISSUE_REGEX.findall(text)))
    return [t for t in unique_issues if t not in ISSUE_BLACKLIST]


def retrieve_commits(project_dir, start_commit, cur_commit='HEAD'):
    git_log_output = subprocess.check_output(
        ['git', '-C', project_dir, 'log',
         f'{start_commit}..{cur_commit}',
         '--format=%H%x00%aN%x00%s%x00%b%x01']).decode()
    return [Commit(*log.strip().split('\x00'))
               for log in git_log_output.split('\x01') if log.strip()]


def parse_subject(commit):
    match = SUBJECT_REGEX.match(commit.subject)
    if match:
        is_valid = True
        symbol = COMMITTYPES[match.group(1)]
        text = match.group(2)
    else:
        is_valid = False
        symbol = ''
        text = commit.subject
    return Subject(is_valid, symbol, text)
