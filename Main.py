from TcpModbus import MODBUSclient as TModebus
from SerialModbus import MODBUSclient as SModebus
from MqttClient import MQTTclient
from Monitor import SysMonitor
import asyncio
import json
import time
import queue
import argparse
import logger

msgque = queue.Queue(0)
devtype = '' #设备类型

def gendate():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

def on_connect(client, userdata, flags, rc):
    logger.writeLog(gendate() + ' MQTT连接成功->'+ str(rc),'tcpMain.log')
    client.subscribe("cmd")

def on_message(client, userdata, msg):
    msgstr = str(msg.payload,'utf-8')
    print(gendate() + " " + msg.topic+"--->"+ msgstr)

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.writeLog(gendate() + ' MQTT连接断开','tcpMain.log')

async def runModbusClient(modbusclient,modbusobj,mqttclient):
    try:
        modbusclient.connect()
    except Exception as e:
        logger.writeLog(gendate() + ' Modbus连接失败！'+ str(e),'tcpMain.log')
    
    while True:
        try:
            rr = modbusclient.read_holding_registers(modbusobj.startaddr, modbusobj.datalen, unit=modbusobj.unit)
            if rr.registers:
                mqttinfo = modbusobj.calcpipe(rr)
                mqttclient.publish(modbusobj.pubtopic,json.dumps(mqttinfo))
        except Exception as e:
            print(gendate() + ' Modbus连接异常，尝试重新连接！' + str(e))
            try:
                modbusclient.close()
            except Exception as e:
                print(gendate() + ' Modbus尝试关闭连接失败！' + str(e))
            
            try:
                modbusclient.connect()
            except Exception as e:
                print(gendate() + ' Modbus尝试重新失败！' + str(e))
            await asyncio.sleep(3)
        finally:
            await asyncio.sleep(modbusobj.interval)


async def runSysMonitorClient(monitorobj,mqttclient):
    while True:
        await asyncio.sleep(monitorobj.interval)
        mqttclient.publish(monitorobj.pubtopic,json.dumps(monitorobj.genSystemInfo()))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Every to MQTT')
    parser.add_argument("-device", type=str, default="noise")
    args = parser.parse_args()
    devtype = args.device

    mqttobj = MQTTclient()
    mqclient = mqttobj.genMQTTClient()
    mqclient.on_connect = on_connect
    mqclient.on_message = on_message
    mqclient.on_disconnect = on_disconnect
    mqclient.connect(mqttobj.host, mqttobj.port, mqttobj.keepalive)

    modbusobj = None
    modclient = None

    if devtype == 'hpu': #如果是HPU则需要初始化为 TCP模式
        modbusobj = TModebus(devtype)
        modclient = modbusobj.genModClient()
    else: #其余默认为RTU模式
        modbusobj = SModebus(devtype)
        modclient = modbusobj.genModClient()

    monitorobj = SysMonitor()

    looper = asyncio.get_event_loop()
    looper.create_task(runModbusClient(modclient,modbusobj,mqclient))    
    if monitorobj.isopen == True:
        looper.create_task(runSysMonitorClient(monitorobj,mqclient))
    
    mqclient.loop_start()
    looper.run_forever()
    
    


    