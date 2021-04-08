import psutil
import yaml
import logger
import copy
import os
import sys
import time

class SysMonitor:
    platform = 'linux' #平台/部分参数 windows及 linux不同
    isopen = False
    pubtopic = 'monitor'
    interval = 120
    devid = ''
    devname = ''
    pubcontent = {
        "devid":'',
        "devname":'',
        "cpu":0,
        "disk":{},
        "virtualmemory":{},
        "swapmemory":{},
        "nic":[]
    }
    feedbacktopic = 'cmd/feedback'
    configobj = None
    
    def __init__(self):
        '''
        初始化，从配置文件读取参数
        '''
        try:
            # 读取配置文件
            f = open("config.yaml","r+",encoding="utf-8")
            fstream = f.read()
            self.configobj = yaml.safe_load(fstream)
            if os.name == 'nt':
                platform = 'windows'
            elif os.name == 'posix':
                platform = 'linux'
            else:
                platform = 'linux'
            self.platform = platform
            self.isopen =self.configobj['monitor']['isopen']
            self.pubtopic = self.configobj['monitor']['pubtopic']
            self.interval = self.configobj['monitor']['interval']
            self.devid = self.configobj['monitor']['devid']
            self.devname = self.configobj['monitor']['devname']
            self.feedbacktopic = self.configobj['monitor']['feedbacktopic'] #执行远程指令反馈
        except Exception as e:
            logger.writeLog("Monitor组件初始化失败" + str(e))
    
    #获取CPU总使用率    
    def getCpu(self):
        return psutil.cpu_percent(0)
    
    #获取整个硬盘使用情况(GB)  sdiskusage(total=21378641920, used=4809781248, free=15482871808, percent=22.5)
    def getDisk(self):
        diskusage = {"total":0,
                     "used":0,
                     "free":0,
                     "percent":0
                    }
        getinfo = psutil.disk_usage('/')
        diskusage['total'] = round(getinfo[0] / 1024 / 1024 / 1024, 2)
        diskusage['used'] = round(getinfo[1] / 1024 / 1024 / 1024, 2)
        diskusage['free'] = round(getinfo[2] / 1024 / 1024 / 1024, 2)
        diskusage['percent'] =round(getinfo[3],2)
        return diskusage
    
    #获取虚拟内存情况 MB
    # svmem(total=10367352832, available=6472179712, percent=37.6, used=8186245120,
    #       free=2181107712, active=4748992512, inactive=2758115328, buffers=790724608, 
    #      cached=3500347392, shared=787554304)
    def getVirtualMemory(self):
        vmemory = {
            "total": 0,
            "available": 0,
            "percent": 0,
            "used": 0,
            "free": 0,
            "active": 0,
            "inactive": 0,
            "buffers": 0,
            "cached": 0,
            "shared": 0,
            "slab": 0,
        }
        getinfo =  psutil.virtual_memory()
        
        if self.platform == 'linux':
            vmemory['total'] = round(getinfo[0]/1024/1024,2)
            vmemory['available'] = round(getinfo[1]/1024/1024,2)
            vmemory['percent'] = round(getinfo[2],2)
            vmemory['used'] = round(getinfo[3]/1024/1024,2)
            vmemory['free'] = round(getinfo[4]/1024/1024,2)
            vmemory['active'] = round(getinfo[5]/1024/1024,2)
            vmemory['inactive'] = round(getinfo[6]/1024/1024,2)
            vmemory['buffers'] = round(getinfo[7]/1024/1024,2)
            vmemory['cached'] = round(getinfo[8]/1024/1024,2)
            vmemory['shared'] = round(getinfo[9]/1024/1024,2)
            vmemory['slab'] = round(getinfo[10]/1024/1024,2)
        elif self.platform == 'windows':
            vmemory['total'] = round(getinfo[0]/1024/1024,2)
            vmemory['available'] = round(getinfo[1]/1024/1024,2)
            vmemory['percent'] = round(getinfo[2],2)
            vmemory['used'] = round(getinfo[3]/1024/1024,2)
            vmemory['free'] = round(getinfo[4]/1024/1024,2)
        
        return vmemory
        

    
    #获取交换分区情况 MB
    # sswap(total=2097147904, used=296128512, free=1801019392, 
    #       percent=14.1, sin=304193536, sout=677842944)
    def getSwapMemory(self):
        smemory = {
            "total": 0,
            "used": 0,
            "free": 0,
            "percent": 0,
            "sin": 0,
            "sout": 0
        }
        getinfo = psutil.swap_memory()
        smemory['total'] = round(getinfo[0]/1024/1024,2)
        smemory['used'] = round(getinfo[1]/1024/1024,2)
        smemory['free'] = round(getinfo[2]/1024/1024,2)
        smemory['percent'] = round(getinfo[3]/1024/1024,2)
        smemory['sin'] = round(getinfo[4]/1024/1024,2)
        smemory['sout'] = round(getinfo[5]/1024/1024,2)
        return smemory

    #获取网卡详情及IP地址
    def getIfconfig(self):
        lista = []
        # 获取网卡信息
        nicinfo = psutil.net_if_addrs()
        # 系统不同取值不同的变量
        locate = 'AF_PACKET'
        if self.platform == 'windows':
            locate = 'AF_LINK'
        for name, datas in nicinfo.items():
            cache = {'name': '', 'macaddr': '', 'ipaddr': '', 'netmask': ''}
            cache['name'] = name
            for data in datas:
                if data.family.name == 'AF_INET':
                    cache['ipaddr'] = data.address
                    cache['netmask'] = data.netmask
                elif data.family.name == locate:
                    cache['macaddr'] = data.address
            lista.append(cache)
        return lista

    def genSystemInfo(self):
        self.pubcontent['devid'] = self.devid
        self.pubcontent['devname'] = self.devname
        self.pubcontent['cpu'] = self.getCpu()
        self.pubcontent['disk'] = self.getDisk()
        self.pubcontent['virtualmemory'] = self.getVirtualMemory()
        self.pubcontent['swapmemory'] = self.getSwapMemory()
        self.pubcontent['nic'] = self.getIfconfig()
        return self.pubcontent
    

    # 更改配置参数
    def updateConfig(self, attr, value):
        #1.修改参数
        #2.修改本地配置文件并返回修改结果（用于向调用方反馈信息）
        flag = False
        if attr in self.configobj.keys(): #如果存在属性值
            if value != None or value != '':
                self.configobj[attr] = value
                with open('config.yaml', "w", encoding="utf-8") as f:
                    yaml.safe_dump(self.configobj, f, allow_unicode=True)
                flag = True
            else:
                logger.writeLog("更新配置文件参数失败,更新属性->" + str(attr) +" 的内容为空->" + str(value))
        else:
            logger.writeLog("更新配置文件参数失败,配置文件不存在属性为->" + str(attr) +" 内容为->" + str(value))
        
        return flag
    
    # 重启程序
    def restartProgram(self, filepath):
        python = sys.executable
        if self.platform == 'windows':
            os.execl(python, '"' + python + '"', filepath)
        elif self.platform == 'linux':
            os.execl(python, python, filepath)

if __name__ == "__main__":
    mo = SysMonitor()
    print(mo.getIfconfig())