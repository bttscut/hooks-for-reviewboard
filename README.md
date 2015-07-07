# hooks-for-reviewboard
for code review based on ReviewBoard


### requirement
1. python > 2.7
2. install RBTools 0.7.4

    	https://www.reviewboard.org/downloads/rbtools/#linux

### config
* logpath

		filepath to write log

* rbcfg_path

		path to place the rbconfig file, rbconfig.py is an example

* rbserver

		reviewboard server url

* rbrepo

		reviewboard server config, which repo to post

* rbadmin rbadminpw

		reviewboard server admin username and passwd

* filter_suffixs

		watch the files with these suffixes

* branch_pattern

		pattern to parse the rb repo branch according to the changed dirs

### usage
使用者只需要将对应的仓库端参数和配置文件路径传给py脚本即可，具体的hook和cron脚本可以用很简单的shell脚本实现。

### svn
在仓库端试用svnlook命令来生成diff并提交，因为仓库段有所有的信息，所以这样比较方便。

### git
rb要求git必须是个webserver能够访问到的local目录，虽然在仓库端也可以像svn一样生成diff发送到server，但是local的目录如果不实时更新，同样会出现找不到文件的错误。思来想去，既然一定需要一个local目录，不如直接做个定时，本地生成算了，又由于git push可以一次性push多个提交，为了完整还原当时提交的现场，于是我用mongodb做了个中转，保存提交信息。

### 为什么不说英文了
因为中国越来越强大了。
