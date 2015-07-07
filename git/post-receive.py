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

#-----------------------config-------------------------
# log
logpath = "/var/log/rb/ttlz-git.log"

# mongodb
host = "172.16.101.243"
port = 27037
dbname = "reviewboard"
colname = "git"
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

logger = init_logger()
error = logger.error
info = logger.info

def run():
    cis = sys.stdin.readline().strip().split()[:3]
    old_value = cis[0]
    new_value = cis[1]
    ref = cis[2]
    doc = {
            "ref":ref,
            "old_value":old_value,
            "new_value":new_value,
            "time":datetime.utctime(),
            "kill":False,
            }
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
