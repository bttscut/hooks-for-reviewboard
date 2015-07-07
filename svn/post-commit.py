#!/usr/bin/python
#coding=utf8

import os, sys
import re
import subprocess
import logging
import logging.handlers
import traceback
from rbtools.api.client import RBClient
from rbtools.api.errors import APIError

#-----------------------config-------------------------
# log
logpath = "/var/log/rb/ttlz-svn.log"

# rbconfig
rbcfg_path = "/home/act/dev/test/rbt/rbconfig.py"
rbserver = "http://bttrb.com"
rbrepo = "svn-test"
rbadmin = "bttrb"
rbadminpw = "123456"

# filter
filter_suffixs = (".cs", ".java", ".c", ".h", ".cpp", ".hpp", ".m", ".mm", ".manifest", ".lua", ".proto", ".py", ".js")

# branch pattern
branch_pattern = "branch/((?:r101)/.+?)/"
#-----------------------config-------------------------

INDEX_FILE_RE = re.compile(b'^Index: (.+?)(?:\t\((added|deleted)\))?\n$')
INDEX_SEP = b'=' * 67

def exit(msg=None):
    if msg:
        print >> sys.stderr, msg
        sys.exit(1)
    else:
        sys.exit(0)

#exit("coming soon")

new_env = {}
new_env["LC_ALL"] = "en_US.UTF-8"
new_env["LANGUAGE"] = "en_US.UTF-8"

def call_cmd(cmd):
    print(cmd)
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, env=new_env)

def init_logger():
    handler = logging.handlers.RotatingFileHandler(logpath, maxBytes = 5*1024*1024, backupCount = 5)
    fmt = "%(asctime)s [%(name)s] %(filename)s[line:%(lineno)d] %(levelname)s %(message)s"
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)
    logger = logging.getLogger('ttlzrb')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

# 读取配置
rbconfig = {}
execfile(rbcfg_path, {}, rbconfig)
REVIEWER_MAP = rbconfig["ReviewerMap"]
AUTHOR_MAP = rbconfig["AuthorMap"]

logger = init_logger()
error = logger.error
info = logger.info

def _process_diff(diff):
    pattern = r"^(?:Added|Deleted|Copied|Modified)(:.*?%s%s)"%(os.linesep, INDEX_SEP)
    diff = re.sub(pattern, r"Index\1", diff, 0, re.M)
    pattern = r"\(Binary files differ\)"
    diff = re.sub(pattern, "Cannot display: file marked as a binary type.", diff, 0, re.M)
    ret = []
    lines = diff.split(os.linesep)
    has_file = True
    for line in lines:
        m = INDEX_FILE_RE.match(line)
        if m:
            fn = m.group(1)
            has_file = fn.endswith(filter_suffixs)
        if has_file:
            ret.append(line)
    return os.linesep.join(ret)

def _process_branch(path):
    m = re.search(branch_pattern, path)
    if m:
        return m.group(1)
    return None

def run():
    # 接收hook参数
    repo = sys.argv[1]
    rev = sys.argv[2]
    look_args = " -r %s %s"%(rev, repo)

    # 是否为感兴趣的分支
    cmd = "svnlook dirs-changed %s"%look_args
    changed_dir = call_cmd(cmd).split(os.linesep)[0].strip() # 取第一行即可
    repo_branch = _process_branch(changed_dir)
    if not repo_branch:
        exit()

    # 是否有代码文件
    interested = False
    cmd = "svnlook changed %s"%look_args
    files = call_cmd(cmd)
    for f in files.split(os.linesep):
        if f.strip().endswith(filter_suffixs):
            interested = True
            break
    if not interested:
        exit()
    
    # 提取rbt post信息
    cmd = "svnlook author %s"%look_args
    author = call_cmd(cmd).strip()
    if author in AUTHOR_MAP:
        author = AUTHOR_MAP[author]
    reviewer = REVIEWER_MAP[author]

    cmd = "svnlook log %s"%look_args
    log = call_cmd(cmd)
    summary = desc = log.strip().replace(os.linesep, "&").replace("\"", "@")
    summary = "rev:%s-[%s]"%(rev, summary)

    cmd = "svnlook diff %s"%look_args
    diff = call_cmd(cmd)
    diff = _process_diff(diff)
    #info("\n"+diff)

    # 创建review_request
    client = RBClient(rbserver, username=rbadmin, password=rbadminpw)
    root = client.get_root()
    request_data = {
            "repository" : rbrepo,
            "commit_id" : rev,
            "submit_as" : author,
            }
    r = root.get_review_requests().create(**request_data)
    vl = root.get_diff_validation()
    basedir = "/"
    #info("------------------"+diff)
    vl.validate_diff(rbrepo, diff, base_dir=basedir)
    r.get_diffs().upload_diff(diff, base_dir=basedir)
    draft = r.get_draft()
    update_data = {
            "branch" : repo_branch,
            "summary" : summary,
            "description" : desc,
            "target_people" : reviewer,
            "public" : True,
            }
            
    ret = draft.update(**update_data)
    info("repo:<%s> rev:<%s> rid:<%s>"%(rbserver, rev, r.id))
    

try:
    run()
except Exception, e:
    error("exception:%s \ntraceback:%s"%(e, traceback.format_exc()))
    exit("see server log")

exit()
