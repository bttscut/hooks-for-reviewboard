#!/usr/bin/python
#coding=utf8

import os, sys
import re
import subprocess
import pymongo
import logging
import logging.handlers
import traceback
from rbtools.api.client import RBClient
from rbtools.api.errors import APIError
import pymongo

#-----------------------config-------------------------
# log
logpath = "/var/log/rb/ttlz-git.log"

# rbconfig
rbcfg_path = "/home/act/dev/test/rbt/rbconfig.py"
rbserver = "http://bttrb.com"
rbrepo = "git-test"
rbadmin = "bttrb"
rbadminpw = "123456"
#-----------------------config-------------------------

def exit(msg=None):
    if msg:
        print >> sys.stderr, msg
        sys.exit(1)
    else:
        sys.exit(0)

new_env = {}
new_env["LC_ALL"] = "en_US.UTF-8"
new_env["LANGUAGE"] = "en_US.UTF-8"

def call_cmd(cmd):
    print(cmd)
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, env=new_env).strip()

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

def run():
    info(os.getcwd())
    cis = sys.stdin.readline().strip().split()[:3]
    old_value = cis[0]
    new_value = cis[1]
    ref = cis[2]
    diff = call_cmd("git diff %s..%s"%(old_value, new_value))
    info(diff)

    ci_range = "%s..%s"%(old_value, new_value)
    # get author name
    cmd = "git log --format=%cn -1 " + new_value
    author = call_cmd(cmd)
    if author in AUTHOR_MAP:
        author = AUTHOR_MAP[author]
    reviewer = REVIEWER_MAP[author]

    # get summary desc
    cmd = "git log --format=%s " + ci_range
    logs = call_cmd(cmd)
    summary = logs.split(os.linesep)[-1]
    cmd = "git log --pretty=fuller " + ci_range
    desc = call_cmd(cmd)

    repo_branch = ref

    # 创建review_request
    client = RBClient(rbserver, username=rbadmin, password=rbadminpw)
    root = client.get_root()
    request_data = {
            "repository" : rbrepo,
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

try:
    run()
except Exception, e:
    error("exception:%s \ntraceback:%s"%(e, traceback.format_exc()))
    exit("see server log")

exit()
