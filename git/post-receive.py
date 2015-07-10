#!/usr/bin/python
#coding=utf8

import os, sys
import re
import subprocess
from datetime import datetime
import pymongo
import logging
import logging.handlers
import traceback

def exit(msg=None):
    if msg:
        print >> sys.stderr, msg
        sys.exit(1)
    else:
        sys.exit(0)

if len(sys.argv) != 3:
    exit("args error")

rbcfg_path = sys.argv[1]
ci_info = sys.argv[2]

# 读取配置
rbcfg = {}
execfile(rbcfg_path, {}, rbcfg)

new_env = {}
new_env["LC_ALL"] = "en_US.UTF-8"
new_env["LANGUAGE"] = "en_US.UTF-8"

def call_cmd(cmd):
    print(cmd)
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, env=new_env).strip()

def init_logger():
    logging.config.fileConfig(rbcfg["logconf"])
    logger = logging.getLogger("root")
    return logger

logger = init_logger()
error = logger.error
info = logger.info

def run():
    cis = ci_info.strip().split()[:3]
    old_value = cis[0]
    new_value = cis[1]
    ref = cis[2]
    doc = {
            "ref":ref,
            "old_value":old_value,
            "new_value":new_value,
            "time":datetime.utcnow(),
            "kill":False,
            }
    host = rbcfg["host"]
    port = rbcfg["port"]
    dbname = rbcfg["dbname"]
    colname = rbcfg["colname"]
    client = pymongo.MongoClient(host, port, w=1, j=True)
    col = client[dbname][colname]
    ret = col.insert_one(doc)
    logmsg = "host[%s]-port[%d]-db[%s]-col[%s]-doc[%s]"%(host, port, dbname, colname, doc)
    info(logmsg)

try:
    run()
except Exception, e:
    error("exception:%s \ntraceback:%s"%(e, traceback.format_exc()))
    exit("see server log")

exit()
