#!/usr/bin/python
#coding=utf8

import os, sys
import re
import subprocess
import logging
import logging.config
import traceback
from rbtools.api.client import RBClient
from rbtools.api.errors import APIError
import pymongo

def exit(msg=None):
    if msg:
        print >> sys.stderr, msg
        sys.exit(1)
    else:
        sys.exit(0)

if len(sys.argv) != 2:
    exit("args error")

rbcfg_path = sys.argv[1]

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
    if sys.version_info[0] == 2 and sys.version_info[1] < 7:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, env=new_env)
        out, err = p.communicate()
        if p.returncode != 0:
            raise Exception("%s failed\nerr:<%s>"%(cmd, err))
        return out
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, env=new_env)

def init_logger():
    logging.config.fileConfig(rbcfg["logconf"])
    logger = logging.getLogger("root")
    return logger

logger = init_logger()
error = logger.error
info = logger.info

def run(old_value, new_value, ref):
    diff = call_cmd("git diff %s..%s"%(old_value, new_value))
    info(diff)

    ci_range = "%s..%s"%(old_value, new_value)
    # get author name
    cmd = "git log --format=%cn -1 " + new_value
    author = call_cmd(cmd).strip()
    if author in AUTHOR_MAP:
        author = AUTHOR_MAP[author]
    reviewer = REVIEWER_MAP[author]

    # get summary desc
    cmd = "git log --format=%s " + ci_range
    logs = call_cmd(cmd)
    summary = logs.split(os.linesep)[0]
    cmd = "git log --pretty=fuller " + ci_range
    desc = call_cmd(cmd)
    summary = summary.replace("\"", "@")
    desc = desc.replace("\"", "@")

    repo_branch = ref.split("/")[-1]

    # 创建review_request
    client = RBClient(rbcfg["rbserver"], username=rbcfg["rbadmin"], password=rbcfg["rbadminpw"])
    root = client.get_root()
    request_data = {
            "repository" : rbcfg["rbrepo"],
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
    info("repo:<%s> rev:<%s> rid:<%s>"%(rbcfg["rbserver"], ci_range, r.id))

client = pymongo.MongoClient(rbcfg["host"], rbcfg["port"], w=1, j=True)
col = client[rbcfg["dbname"]][rbcfg["colname"]]
it = col.find({"kill":False}, sort = [("time", pymongo.ASCENDING)])
if it.count() == 0:
    exit()

os.chdir(rbcfg["repo_path"])
call_cmd("git pull")
has_err = False
_ids = []
for i in it:
    try:
        run(i["old_value"], i["new_value"], i["ref"])
    except Exception, e:
        error("exception:%s \ntraceback:%s"%(e, traceback.format_exc()))
        has_err = True
    _ids.append(i["_id"])

try:
    requests = []
    for i in _ids:
        requests.append(pymongo.UpdateOne({"_id":i}, {"$set":{"kill":True}}))
    col.bulk_write(requests)
except Exception, e:
    error("exception:%s \ntraceback:%s"%(e, traceback.format_exc()))
    has_err = True

if has_err:
    exit("see server log")
else:
    exit()
