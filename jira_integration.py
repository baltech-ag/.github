#!python3

import base64
import re
import os
import io
from collections import defaultdict
from urllib import request

from common import retrieve_commits, parse_subject


TICKET_REGEX = re.compile(r'\b[A-Za-z]{2,4}-\d+\b')
TICKET_BLACKLIST = ("RS-232",)

JIRA_URL = 'JIRA_URL'
JIRA_USER = 'JIRA_USER'
JIRA_PASSWORD = 'JIRA_PASSWORD'
SERVER_URL = 'CI_SERVER_URL'
START_COMMIT = 'CI_COMMIT_BEFORE_SHA'
CUR_COMMIT = 'CI_COMMIT_SHA'
BRANCH_NAME = 'CI_COMMIT_REF_NAME'
PROJECT_NAME = 'CI_PROJECT_NAME'
PROJECT_NAMESPACE = 'CI_PROJECT_NAMESPACE'
PROJECT_DIR = 'CI_PROJECT_DIR'


def group_by_issue(commits):
    affected_issues = defaultdict(list)
    for commit in commits:
        commit_msg = f'{commit.subject}\n{commit.body}'
        for ticket in set(map(str.upper, TICKET_REGEX.findall(commit_msg))):
            if ticket not in TICKET_BLACKLIST:
                affected_issues[ticket].append(commit)
    return dict(affected_issues)


def convert_to_comment(commits, server_url, branch_name,
                       project_name, project_namespace):
    comment = io.StringIO()
    bgcolor = '#deebff' if branch_name == 'master' else '#ffffce'
    comment.write(f'{{panel:bgColor={bgcolor}|borderStyle=none}}\n')
    authors = set()
    for commit in commits:
        subject = parse_subject(commit)
        comment.write(
            f"{subject.symbol} "
            f"[{subject.text}|"
            f"{server_url}/{project_namespace}/{project_name}"
            f"/-/commit/{commit.commitid}]\n")
        authors.add(commit.author)
    comment.write('\n')
    comment.write(
        f'{{color:#4c9aff}}{" ".join(authors)} contributed to '
        f'[{project_name}|{server_url}/{project_namespace}/{project_name}'
        f'/-/tree/{branch_name}]')
    if branch_name != 'master':
        comment.write(f' at *{branch_name}*')
    comment.write('{color}\n')
    comment.write('{panel}')
    return comment.getvalue()


def append_comment(issue, comment, jira_url, jira_user, jira_password):
    escaped_comment = comment \
        .replace('\\', '\\\\') \
        .replace('"', '\\"') \
        .replace('\r\n', '\n') \
        .replace('\n', '\\n')
    base64_auth = base64.b64encode(f'{jira_user}:{jira_password}'.encode())
    req = request.Request(
        f'{jira_url}/rest/api/2/issue/{issue}/comment',
        headers={
            'Authorization': 'Basic ' + base64_auth.decode(),
            'Content-Type': 'application/json',
        },
        data=f'{{"body": "{escaped_comment}"}}'.encode()
    )
    request.urlopen(req)


def create_jira_comment():
    env = os.environ
    new_branch = all(c == '0' for c in env[START_COMMIT])
    all_commits = retrieve_commits(
        env[PROJECT_DIR],
        'origin/master' if new_branch else env[START_COMMIT],
        env[CUR_COMMIT])
    affected_issues = group_by_issue(all_commits)
    for issue, commits in affected_issues.items():
        print("Creating comment in {} with {}".format(
            issue,
            "1 commit" if len(commits) == 1 else "{} commits".format(len(commits)),
        ))
        comment = convert_to_comment(
            reversed(commits),
            env[SERVER_URL],
            env[BRANCH_NAME],
            env[PROJECT_NAME],
            env[PROJECT_NAMESPACE])
        append_comment(
            issue,
            comment,
            env[JIRA_URL],
            env[JIRA_USER],
            env[JIRA_PASSWORD])


def main():
    create_jira_comment()


if __name__ == '__main__':
    main()
