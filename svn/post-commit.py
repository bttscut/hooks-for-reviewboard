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

def exit(msg=None):
    if msg:
        print >> sys.stderr, msg
        sys.exit(1)
    else:
        sys.exit(0)


# 接收hook参数
if len(sys.argv) != 4:
    exit("args error")
rbcfg_path = sys.argv[1]
repo = sys.argv[2]
rev = sys.argv[3]

INDEX_FILE_RE = re.compile(b'^Index: (.+?)(?:\t\((added|deleted)\))?\n$')
INDEX_SEP = b'=' * 67

new_env = {}
new_env["LC_ALL"] = "en_US.UTF-8"
new_env["LANGUAGE"] = "en_US.UTF-8"

# 读取配置
rbcfg = {}
execfile(rbcfg_path, {}, rbcfg)
REVIEWER_MAP = rbcfg["ReviewerMap"]
AUTHOR_MAP = rbcfg["AuthorMap"]


def call_cmd(cmd):
    print(cmd)
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, env=new_env)

def init_logger():
    logging.config.fileConfig(rbcfg["logconf"])
    logger = logging.getLogger("root")
    return logger

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
            has_file = fn.endswith(rbcfg["filter_suffixs"])
        if has_file:
            ret.append(line)
    return os.linesep.join(ret)

def _process_branch(path):
    m = re.search(rbcfg["branch_pattern"], path)
    if m:
        return m.group(1)
    return None

def run():
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
        if f.strip().endswith(rbcfg["filter_suffixs"]):
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
    client = RBClient(rbcfg["rbserver"], username=rbcfg["rbadmin"], password=rbcfg["rbadminpw"])
    root = client.get_root()
    request_data = {
            "repository" : rbcfg["rbrepo"],
            #"commit_id" : rev,
            "submit_as" : author,
            }
    r = root.get_review_requests().create(**request_data)
    vl = root.get_diff_validation()
    basedir = "/"
    #info("------------------"+diff)
    vl.validate_diff(rbcfg["rbrepo"], diff, base_dir=basedir)
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
    info("repo:<%s> rev:<%s> rid:<%s>"%(rbcfg["rbserver"], rev, r.id))
    

try:
    run()
except Exception, e:
    error("rev:<%s> exception:%s \ntraceback:%s"%(rev, e, traceback.format_exc()))
    exit("see server log")

exit()
