#! /usr/bin/python3.8
## Alarm Server
## Supporting Envisalink 2DS/3/4
## Written by donnyk+envisalink@gmail.com
## Lightly improved by leaberry@gmail.com
## SmartThings away/stay mode by jordan@xeron.cc
## Updated for Python 3.8 by ralphtorchia1@gmail.com
##
## This code is under the terms of the GPL v3 license.
## Date: 2020-10-12


import asyncore, asynchat
import configparser
import datetime
import os, socket, string, sys, http.client, urllib.request, urllib.parse, urllib.error, urllib.parse, ssl
import io, email
import json
import hashlib
import time
import getopt
import requests
import logging
from logging.handlers import RotatingFileHandler

from envisalinkdefs import evl_ResponseTypes
from envisalinkdefs import evl_Defaults
from envisalinkdefs import evl_ArmModes

LOGTOFILE = False

class CodeError(Exception): pass

ALARMSTATE={"version" : 0.1}
MAXPARTITIONS=16
MAXZONES=64
MAXALARMUSERS=95
EVENTCODES=[510,511,601,602,603,604,605,606,609,610,616,620,621,622,623,624,625,626,650,651,652,653,654,655,656,657,663,664,840,841]
CONNECTEDCLIENTS={}

def dict_merge(a, b):
    c = a.copy()
    c.update(b)
    return c

def getMessageType(code):
    return evl_ResponseTypes[code]

def alarmserver_logger(message, type = 0, level = 0):
    log_msg = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))+" "+message
    if LOGTOFILE:
        outfile.info(log_msg)
    else:
        print(log_msg)
    
def to_chars(string):
    chars = []
    for char in string:
        chars.append(ord(char))
    return chars

def get_checksum(code, data):
    strcheck = sum(to_chars(code)+to_chars(data))
    return format(strcheck, "02X")[-2:]

# currently supports pushover notifications
# more can be added, including email, text, etc.
# to be fixed!
def send_notification(config, message):
    if config.PUSHOVER_ENABLE == True:
        conn = http.client.HTTPSConnection("api.pushover.net:443")
        conn.request("POST", "/1/messages.json",
            urllib.parse.urlencode({
            "token": "qo0nwMNdX56KJl0Avd4NHE2onO4Xff",
            "user": config.PUSHOVER_USERTOKEN,
            "message": str(message),
            }), { "Content-type": "application/x-www-form-urlencoded" })

def convert_bstr(string, type = 0):
    if type == "":
        return string
    if type == "encoder":
        return string.encode("utf-8")
    if type == "decoder":
        return string.decode("utf-8")

class AlarmServerConfig():
    def __init__(self, configfile):

        self._config = configparser.ConfigParser()
        self._config.read(configfile)

        self.LOGURLREQUESTS = self.read_config_var("alarmserver", "logurlrequests", True, "bool")
        self.LOGMAXSIZE = self.read_config_var("alarmserver","logmaxsize", 102400, "int")
        self.LOGMAXBACKUPS = self.read_config_var("alarmserver", "logmaxbackups", 5, "int")
        self.HTTPPORT = self.read_config_var("alarmserver", "httpport", 8111, "int")
        self.CERTFILE = self.read_config_var("alarmserver", "certfile", "server.crt", "str")
        self.KEYFILE = self.read_config_var("alarmserver", "keyfile", "server.key", "str")
        self.MAXEVENTS = self.read_config_var("alarmserver", "maxevents", 10, "int")
        self.MAXALLEVENTS = self.read_config_var("alarmserver", "maxallevents", 100, "int")
        self.ENVISALINKHOST = self.read_config_var("envisalink", "host", "envisalink", "str")
        self.ENVISALINKPORT = self.read_config_var("envisalink", "port", 4025, "int")
        self.ENVISALINKPASS = self.read_config_var("envisalink", "pass", "user", "str")
        self.ENABLEPROXY = self.read_config_var("envisalink", "enableproxy", True, "bool")
        self.ENVISALINKPROXYPORT = self.read_config_var("envisalink", "proxyport", self.ENVISALINKPORT, "int")
        self.ENVISALINKPROXYPASS = self.read_config_var("envisalink", "proxypass", self.ENVISALINKPASS, "str")
        self.PUSHOVER_ENABLE = self.read_config_var("pushover", "enable", False, "bool")
        self.PUSHOVER_USERTOKEN = self.read_config_var("pushover", "usertoken", "", "str")
        self.ALARMCODE = self.read_config_var("envisalink", "alarmcode", "1111", "str")
        self.EVENTTIMEAGO = self.read_config_var("alarmserver", "eventtimeago", True, "bool")
        self.LOGFILE = self.read_config_var("alarmserver", "logfile", "", "str")
        self.CALLBACKURL_BASE = self.read_config_var("alarmserver", "callbackurl_base", "", "str").rstrip("/")
        self.CALLBACKURL_APP_ID = self.read_config_var("alarmserver", "callbackurl_app_id", "", "str")
        self.CALLBACKURL_ACCESS_TOKEN = self.read_config_var("alarmserver", "callbackurl_access_token", "", "str")
        global LOGTOFILE
        if self.LOGFILE == "":
            LOGTOFILE = False
        else:
            LOGTOFILE = True

        self.PARTITIONNAMES={}
        self.PARTITIONS={}
        for i in range(1, MAXPARTITIONS+1):
            self.PARTITIONNAMES[i]=self.read_config_var("partition"+str(i), "name", "", "str", True)
            stay=self.read_config_var("partition"+str(i), "stay", "", "str", True)
            away=self.read_config_var("partition"+str(i), "away", "", "str", True)
            simplestay=self.read_config_var("partition"+str(i), "simplestay", "", "str", True)
            simpleaway=self.read_config_var("partition"+str(i), "simpleaway", "", "str", True)
            if (stay!="") or (away!="") or (simplestay!="") or (simpleaway!=""):
                self.PARTITIONS[i] = {}
                if away!="":
                    self.PARTITIONS[i]["away"]=away
                if stay!="":
                    self.PARTITIONS[i]["stay"]=stay
                if simpleaway!="":
                    self.PARTITIONS[i]["simpleaway"]=simpleaway
                if simplestay!="":
                    self.PARTITIONS[i]["simplestay"]=simplestay

        self.ZONES={}
        self.ZONENAMES={}
        for i in range(1, MAXZONES+1):
            self.ZONENAMES[i]=self.read_config_var("zone"+str(i), "name", "", "str", True)
            type = self.read_config_var("zone"+str(i), "type", "", "str", True)
            partition = self.read_config_var("zone"+str(i), "partition", "1", "str", True)
                        
            if (self.ZONENAMES[i]!="" and type!=""):
                self.ZONES[i] = {}
                self.ZONES[i]["name"] = self.ZONENAMES[i]
                self.ZONES[i]["type"] = type
                self.ZONES[i]["partition"] = partition

        self.ALARMUSERNAMES={}
        for i in range(1, MAXALARMUSERS+1):
            self.ALARMUSERNAMES[i]=self.read_config_var("alarmserver", "user"+str(i), "", "str", True)

        if self.PUSHOVER_USERTOKEN == "" and self.PUSHOVER_ENABLE == True: self.PUSHOVER_ENABLE = False

    def read_config_var(self, section, variable, default, type = "str", quiet = False):
        try:
            if type == "str":
                return self._config.get(section,variable)
            elif type == "bool":
                return self._config.getboolean(section,variable)
            elif type == "int":
                return int(self._config.get(section,variable))
        except (configparser.NoSectionError, configparser.NoOptionError):
            self.defaulting(section, variable, default, quiet)
            return default

    def defaulting(self, section, variable, default, quiet = False):
        if quiet == False:
            print(("Config option "+ str(variable) + " not set in ["+str(section)+"] defaulting to: \""+str(default)+"\""))

class DeviceSetup():
    def __init__(self, config):
        self._config = config

        # prepare partition and zone json for device creation
        partitionjson = json.dumps(config.PARTITIONS)
        zonejson = json.dumps(config.ZONES)

        headers = {"content-type": "application/json"}

        # create zone devices
        myURL = config.CALLBACKURL_BASE + "/" + config.CALLBACKURL_APP_ID + "/installzones" + "?access_token=" + config.CALLBACKURL_ACCESS_TOKEN
        if (config.LOGURLREQUESTS):
          alarmserver_logger("myURL: %s" % myURL)
        requests.post(myURL, data=zonejson, headers=headers)

        # create partition devices
        myURL = config.CALLBACKURL_BASE + "/" + config.CALLBACKURL_APP_ID + "/installpartitions" + "?access_token=" + config.CALLBACKURL_ACCESS_TOKEN
        if (config.LOGURLREQUESTS):
          alarmserver_logger("myURL: %s" % myURL)
        requests.post(myURL, data=partitionjson, headers=headers)

class HTTPChannel(asynchat.async_chat):
    def __init__(self, server, sock, addr):
        asynchat.async_chat.__init__(self, sock)
        self.server = server
        self.set_terminator(b"\r\n\r\n")
        self.header = None
        self.data = b""
        self.shutdown = 0

    def collect_incoming_data(self, data):
        self.data = self.data + data
        if len(self.data) > 16384:
        # limit the header size to prevent attacks
            self.shutdown = 1

    def found_terminator(self):
        if not self.header:
            # parse http header
            fp = io.StringIO(self.data.decode("utf-8"))
            request = fp.readline().split()
            if len(request) != 3:
                # badly formed request; just shut down
                self.shutdown = 1
            else:
                # parse message header
                self.header = email.message.Message(fp)
                self.set_terminator(b"\r\n")
                self.server.handle_request(
                    self, request[0], request[1], self.header
                    )
                self.close_when_done()
            self.data = ""
        else:
            pass # ignore body data, for now

    def pushstatus(self, status, explanation="OK"):
        self.push(convert_bstr("HTTP/1.0 %d %s\r\n" % (status, explanation), "encoder"))

    def pushok(self, content):
        self.pushstatus(200, "OK")
        self.push(convert_bstr("Content-type: application/json\r\n", "encoder"))
        self.push(convert_bstr("Expires: Sat, 26 Jul 1997 05:00:00 GMT\r\n", "encoder"))
        self.push(convert_bstr("Last-Modified: "+ datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")+" GMT\r\n", "encoder"))
        self.push(convert_bstr("Cache-Control: no-store, no-cache, must-revalidate\r\n", "encoder"))
        self.push(convert_bstr("Cache-Control: post-check=0, pre-check=0\r\n", "encoder"))
        self.push(convert_bstr("Pragma: no-cache\r\n", "encoder"))
        self.push(b"\r\n")
        self.push(convert_bstr(content,"encoder"))

    def pushfile(self, file):
        self.pushstatus(200, b"OK")
        extension = os.path.splitext(file)[1]
        if extension == ".html":
            self.push(b"Content-type: text/html\r\n")
        elif extension == ".js":
            self.push(b"Content-type: text/javascript\r\n")
        elif extension == ".png":
            self.push(b"Content-type: image/png\r\n")
        elif extension == ".css":
            self.push(b"Content-type: text/css\r\n")
        self.push(b"\r\n")
        self.push_with_producer(push_FileProducer(sys.path[0] + os.sep + "ext" + os.sep + file))

class EnvisalinkClient(asynchat.async_chat):
    def __init__(self, config):
        # Call parent class's __init__ method
        asynchat.async_chat.__init__(self)

        # Define some private instance variables
        self._buffer = []

        # Are we logged in?
        self._loggedin = False

        # Set our terminator to \n
        self.set_terminator(b"\r\n")

        # Set copy of config
        self._config = config

        # Reconnect delay
        self._retrydelay = 10

        self.do_connect()

    def do_connect(self, reconnect = False):
        # Create the socket and connect to the server
        if reconnect == True:
            alarmserver_logger("Connection failed, retrying in " + str(self._retrydelay) + " seconds")
            for i in range(0, self._retrydelay):
                time.sleep(1)

        self.create_socket()
        try:
            self.connect((self._config.ENVISALINKHOST, self._config.ENVISALINKPORT))
        except socket.error as err:
            alarmserver_logger("Error with socket.connect: %s" % (err))
            raise

    def collect_incoming_data(self, data):
        # Append incoming data to the buffer
        self._buffer.append(data.decode("utf-8"))
        
    def found_terminator(self):
        line = "".join(self._buffer)
        self.handle_line(line)
        self._buffer = []
        
    def handle_connect(self):
        alarmserver_logger("Connected to %s:%i" % (self._config.ENVISALINKHOST, self._config.ENVISALINKPORT))

    def handle_close(self):
        self._loggedin = False
        self.close()
        alarmserver_logger("Disconnected from %s:%i" % (self._config.ENVISALINKHOST, self._config.ENVISALINKPORT))
        self.do_connect(True)

    def handle_error(self):
        self._loggedin = False
        self.close()
        alarmserver_logger("Error, disconnected from %s:%i" % ( self._config.ENVISALINKHOST, self._config.ENVISALINKPORT))
        Print ("ERROR", msg = sys.stderror)
        self.do_connect(True)

    def send_command(self, code, data, checksum = True):
        if checksum == True:
            to_send = code+data+get_checksum(code,data)+"\r\n"
        else:
            to_send = code+data+"\r\n"
        
        alarmserver_logger("TX > "+to_send[:-1])
        self.push(to_send.encode("utf-8"))

    def handle_line(self, input):
        if input != "":
            for client in CONNECTEDCLIENTS:
                CONNECTEDCLIENTS[client].send_command(input, False)
            try:
                code=int(input[:3])
                parameters=input[3:][:-2]
                event = getMessageType(code)
                message = self.format_event(event, parameters)
                alarmserver_logger("RX < " + str(code) +" - " + parameters + " - " + message)

                try:
                    handler = "handle_%s" % evl_ResponseTypes[code]["handler"]
                except KeyError:
                    #call general event handler
                    self.handle_event(code, parameters, event, message)
                    return

                try:
                    func = getattr(self, handler)
                except AttributeError:
                    raise CodeError("Handler function doesn't exist")

                func(code, parameters, event, message)
                
            except:
                alarmserver_logger("Unsupported input! This could be a bug. Input was:" +str(input))

    def format_event(self, event, parameters):
        if "type" in event:
            if event["type"] in ("partition", "zone"):
                if event["type"] == "partition":
                    # If parameters includes extra digits then this next line would fail
                    # without looking at just the first digit which is the partition number
                    if int(parameters[0]) in self._config.PARTITIONNAMES and self._config.PARTITIONNAMES[int(parameters[0])]!="":
                        # After partition number can be either a usercode
                        # or for event 652 a type of arm mode (single digit)
                        # Usercode is always 4 digits padded with zeros
                        if len(str(parameters)) == 5:
                            # We have a usercode
                            try:
                                usercode = int(parameters[1:5])
                            except:
                                usercode = 0
                            if int(usercode) in self._config.ALARMUSERNAMES:
                                if self._config.ALARMUSERNAMES[int(usercode)]!=False:
                                    alarmusername = self._config.ALARMUSERNAMES[int(usercode)]
                                else:
                                    # Didn't find a username, use the code instead
                                    alarmusername = usercode
                                return event["name"].format(str(self._config.PARTITIONNAMES[int(parameters[0])]), str(alarmusername))
                        elif len(parameters) == 2:
                            # We have an arm mode instead, get it's friendly name
                            armmode = evl_ArmModes[int(parameters[1])]
                            return event["name"].format(str(self._config.PARTITIONNAMES[int(parameters[0])]), str(armmode))
                        elif len(parameters) == 1:
                            return event["name"].format(str(self._config.PARTITIONNAMES[int(parameters)]))
                        else:
                            return event["name"].format(str(self._config.PARTITIONNAMES[int(parameters[0])]), int(parameters[1:]))
                elif event["type"] == "zone":
                    if int(parameters) in self._config.ZONENAMES and self._config.ZONENAMES[int(parameters)]!="":
                        return event["name"].format(str(self._config.ZONENAMES[int(parameters)]))
        return event["name"].format(str(parameters))

    # envisalink event handlers, some events are unhandeled.
    def handle_login(self, code, parameters, event, message):
        if parameters == "3":
            self._loggedin = True
            self.send_command("005", self._config.ENVISALINKPASS)
        if parameters == "1":
            self.send_command("001", "")
            # this was to update bypass status, but sometimes would change alarm arm status from stay/away
            # time.sleep(2)
            # self.send_command("071", "1*1#")
        if parameters == "0":
            alarmserver_logger("Incorrect envisalink password")
            sys.exit(0)

    def handle_event(self, code, parameters, event, message):
        if "type" in event:
            if not event["type"] in ALARMSTATE: ALARMSTATE[event["type"]]={"lastevents" : []}

            if event["type"] in ("partition", "zone"):
                if event["type"] == "zone":
                    if int(parameters) in self._config.ZONENAMES:
                        if self._config.ZONENAMES[int(parameters)]!="":
                            if not int(parameters) in ALARMSTATE[event["type"]]:
                                ALARMSTATE[event["type"]][int(parameters)] = {"name" : self._config.ZONENAMES[int(parameters)]}
                        else:
                            if not int(parameters) in ALARMSTATE[event["type"]]: ALARMSTATE[event["type"]][int(parameters)] = {}
                elif event["type"] == "partition":
                    if int(parameters[0]) in self._config.PARTITIONNAMES:
                        if self._config.PARTITIONNAMES[int(parameters[0])]!="":
                            if not int(parameters) in ALARMSTATE[event["type"]]: ALARMSTATE[event["type"]][int(parameters)] = {"name" : self._config.PARTITIONNAMES[int(parameters)]}
                        else:
                            if not int(parameters) in ALARMSTATE[event["type"]]: ALARMSTATE[event["type"]][int(parameters)] = {}
            else:
                if not int(parameters) in ALARMSTATE[event["type"]]: ALARMSTATE[event["type"]][int(parameters)] = {}

            if not "lastevents" in ALARMSTATE[event["type"]][int(parameters)]: ALARMSTATE[event["type"]][int(parameters)]["lastevents"] = []
            if not "status" in ALARMSTATE[event["type"]][int(parameters)]:
                if not "type" in event:
                    ALARMSTATE[event["type"]][int(parameters)]["status"] = {}
                else:
                    ALARMSTATE[event["type"]][int(parameters)]["status"] = evl_Defaults[event["type"]]

            if "status" in event:
                ALARMSTATE[event["type"]][int(parameters)]["status"]=dict_merge(ALARMSTATE[event["type"]][int(parameters)]["status"], event["status"])

            if len(ALARMSTATE[event["type"]][int(parameters)]["lastevents"]) > self._config.MAXEVENTS:
                ALARMSTATE[event["type"]][int(parameters)]["lastevents"].pop(0)
            ALARMSTATE[event["type"]][int(parameters)]["lastevents"].append({"datetime" : str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), "message" : message})

            if len(ALARMSTATE[event["type"]]["lastevents"]) > self._config.MAXALLEVENTS:
                ALARMSTATE[event["type"]]["lastevents"].pop(0)
            ALARMSTATE[event["type"]]["lastevents"].append({"datetime" : str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), "message" : message})
        self.callbackurl_event(code, parameters, event, message)

    def handle_zone(self, code, parameters, event, message):
        self.handle_event(code, parameters[1:], event, message)

    def handle_partition(self, code, parameters, event, message):
        self.handle_event(code, parameters[0], event, message)

    def callbackurl_event(self, code, parameters, event, message):
        # Determine what events we are sending to smartthings then send if we match
        if code in EVENTCODES:
           # Check for events with no type by code instead
           if code == 620:
             update = {
               "type": "partition",
               "value": "1",
               "status": "duress"
             }
           elif code == 616:
             update = {
               "type": "bypass",
               "status": "bypass",
               "parameters": {}
             }

             begin=0
             end=2
             count=8
             binary = bin(int(str(parameters[begin:end]), 16))[2:].zfill(8)

             for zone in range(1, MAXZONES+1):
               if count < 1:
                 count = 8
                 begin = begin + 2
                 end = end + 2
                 binary = bin(int(str(parameters[begin:end]), 16))[2:].zfill(8)
               count = count - 1
               # Is our zone setup with a custom name, if so we care about it
               if zone in self._config.ZONENAMES and self._config.ZONENAMES[zone]!="":
                 value = "on" if (binary[count] == "1") else "off"
                 update["parameters"][str(zone)]=value
           elif code in [510,511]:
             codeMap = {
               510:"led",
               511:"ledflash",
             }

             ledMap = {
               0:"backlight",
               1:"fire",
               2:"program",
               3:"trouble",
               4:"bypass",
               5:"memory",
               6:"armed",
               7:"ready"
             }

             update = {
               "type": "partition",
               "value": "1",
               "status": codeMap[code],
               "parameters": {}
             }

             binary = bin(int(str(parameters), 16))[2:].zfill(8)

             for i in range(0, 8):
               value = "on" if (binary[i] == "1") else "off"
               update["parameters"][ledMap[i]]=value
           elif event["type"] == "system":
             codeMap = {
               621:"keyfirealarm",
               622:"keyfirerestore",
               623:"keyauxalarm",
               624:"keyauxrestore",
               625:"keypanicalarm",
               626:"keypanicrestore",
             }

             update = {
               "type": "partition",
               "value": "1",
               "status": codeMap[code],
             }
           elif event["type"] == "partition":
             # Is our partition setup with a custom name?
             if int(parameters[0]) in self._config.PARTITIONNAMES and self._config.PARTITIONNAMES[int(parameters[0])]!="":
               if code == 655:
                 self.send_command("071", "1*1#")

               codeMap = {
                 650:"ready",
                 651:"notready",
                 653:"forceready",
                 654:"alarm",
                 655:"disarm",
                 656:"exitdelay",
                 657:"entrydelay",
                 663:"chime",
                 664:"nochime",
                 701:"armed",
                 702:"armed",
                 840:"trouble",
                 841:"restore",
               }

               update = {
                 "type": "partition",
                 "name": self._config.PARTITIONNAMES[int(parameters[0])],
                 "value": str(int(parameters[0]))
               }

               if code == 652:
                 if message.endswith("Zero Entry Away"):
                   update["status"]="instantaway"
                 elif message.endswith("Zero Entry Stay"):
                   update["status"]="instantstay"
                 elif message.endswith("Away"):
                   update["status"]="away"
                 elif message.endswith("Stay"):
                   update["status"]="stay"
                 else:
                   update["status"]="armed"
               else:
                   update["status"]=codeMap[code]
             else:
               # We don't care about this partition
               return
           elif event["type"] == "zone":
             # Is our zone setup with a custom name, if so we care about it
             if int(parameters) in self._config.ZONENAMES and self._config.ZONENAMES[int(parameters)]!="":
               codeMap = {
                 601:"alarm",
                 602:"noalarm",
                 603:"tamper",
                 604:"restore",
                 605:"fault",
                 606:"restore",
                 609:"open",
                 610:"closed",
                 631:"smoke",
                 632:"clear",
               }

               update = {
                 "type": "zone",
                 "name": self._config.ZONENAMES[int(parameters)],
                 "value": str(int(parameters)),
                 "status": codeMap[code]
               }
             else:
               # We don't care about this zone
               return
           else:
             # Unhandled event type..
             return

           # If we made it here we should send to Smartthings
           try:
             # Note: I don't currently care about the return value, fire and forget right now
             jsonupdate = json.dumps(update)
             headers = {"content-type": "application/json"}
             # send json update
             myURL = config.CALLBACKURL_BASE + "/" + config.CALLBACKURL_APP_ID + "/update" + "?access_token=" + config.CALLBACKURL_ACCESS_TOKEN
             if (config.LOGURLREQUESTS):
               alarmserver_logger("myURL: %s" % myURL)
             requests.post(myURL, data=jsonupdate, headers=headers)

             # print "myURL: ", myURL
             # print "Exit code: ", r.status_code
             # print "Response data: ", r.text
             # time.sleep(0.5)
           except:
             print(sys.exc_info()[0])

class push_FileProducer:
    # a producer which reads data from a file object
    def __init__(self, file):
        self.file = open(file, "rb")

    def more(self):
        if self.file:
            data = self.file.read(2048)
            if data:
                return data
            self.file = None
        return ""

class AlarmServer(asyncore.dispatcher):
    def __init__(self, config):
        # Call parent class's __init__ method
        asyncore.dispatcher.__init__(self)

        # Create Envisalink client object
        try:
            self._envisalinkclient = EnvisalinkClient(config)
        except:
            alarmserver_logger("Error in Envisalink settings.")
            raise

        # Store config
        self._config = config

        # Create socket and listen on it
        self.create_socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind(("", config.HTTPPORT))
        self.listen(5)

    def handle_accept(self):
        # Accept the connection
        conn, addr = self.accept()
        if (config.LOGURLREQUESTS):
            alarmserver_logger("Incoming web connection from %s" % repr(addr))

        try:
            HTTPChannel(self, conn, addr)
            # HTTPChannel(self, ssl.wrap_socket(conn, server_side=True, certfile=config.CERTFILE, keyfile=config.KEYFILE, ssl_version=ssl.PROTOCOL_TLSv1), addr)
        except ssl.SSLError:
            return

    def handle_request(self, channel, method, request, header):
        if (config.LOGURLREQUESTS):
            alarmserver_logger("Web request: "+str(method)+" "+str(request))

        query = urllib.parse.urlparse(request)
        query_array = urllib.parse.parse_qs(query.query, True)
        if "alarmcode" in query_array:
            alarmcode=str(query_array["alarmcode"][0])
        else:
            alarmcode=str(self._config.ALARMCODE)

        if "part" in query_array:
            part=str(query_array["part"][0])
        else:
            part="1"

        if query.path == "/":
            channel.pushfile("index.html");
        elif query.path == "/api":
            channel.pushok(json.dumps(ALARMSTATE))
        elif query.path == "/api/alarm/arm":
            channel.pushok(json.dumps({"response" : "Request to arm received"}))
            self._envisalinkclient.send_command("030", part)
        elif query.path == "/api/alarm/stayarm":
            channel.pushok(json.dumps({"response" : "Request to arm in stay received"}))
            self._envisalinkclient.send_command("031", part)
        elif query.path == "/api/alarm/toggleinstant":
            channel.pushok(json.dumps({"response" : "Request to toggle instant mode received"}))
            self._envisalinkclient.send_command("032", part)
        elif query.path == "/api/alarm/instantarm":
            channel.pushok(json.dumps({"response" : "Request to arm in instant mode received"}))
            self._envisalinkclient.send_command("071", part + "*9" + alarmcode + "#")
        elif query.path == "/api/alarm/togglenight":
            channel.pushok(json.dumps({"response" : "Request to toggle night mode received"}))
            self._envisalinkclient.send_command("071", part + "**#")
        elif query.path == "/api/alarm/togglechime":
            channel.pushok(json.dumps({"response" : "Request to toggle chime mode received"}))
            self._envisalinkclient.send_command("071", part + "*4#")
        elif query.path == "/api/alarm/armwithcode":
            channel.pushok(json.dumps({"response" : "Request to arm with code received"}))
            self._envisalinkclient.send_command("033", part + alarmcode)
        elif query.path == "/api/alarm/bypass":
            try:
                zones = str(query_array["zone"][0]).split(",")
                for zone in zones:
                    if str(zone) == "0":
                      partition = part
                    else:
                      partition = str(self._config.ZONES[int(zone)]["partition"])
                    if len(zone) == 1: zone = "0" + zone
                    alarmserver_logger("request to bypass zone %s on partition %s" % (zone, partition))
                    channel.pushok(json.dumps({"response" : "Request to bypass zone received"}))
                    self._envisalinkclient.send_command("071", partition + "*1" + str(zone) + "#")
                    time.sleep(2)
            except:
                channel.pushok(json.dumps({"response" : "Request to bypass zone received but invalid zone given!"}))
        elif query.path == "/api/alarm/panic":
            try:
                type = str(query_array["type"][0])
                alarmserver_logger("request to panic type %s" % type)
                channel.pushok(json.dumps({"response" : "Request to panic received"}))
                self._envisalinkclient.send_command("060", str(type))
            except:
                channel.pushok(json.dumps({"response" : "Request to panic received but invalid type given!"}))
        elif query.path == "/api/alarm/reset":
            channel.pushok(json.dumps({"response" : "Request to reset sensors received"}))
            self._envisalinkclient.send_command("071", part + "*72#")
        elif query.path == "/api/alarm/refresh":
            channel.pushok(json.dumps({"response" : "Request to refresh received"}))
            self._envisalinkclient.send_command("001", "")
            time.sleep(2)
            self._envisalinkclient.send_command("071", part + "*1#")
        elif query.path == "/api/pgm":
            channel.pushok(json.dumps({"response" : "Request to trigger PGM"}))
            # self._envisalinkclient.send_command("020", "1" + str(query_array["pgmnum"][0]))
            self._envisalinkclient.send_command("071", part + "*7" + str(query_array["pgmnum"][0]) + "#")
            # time.sleep(1)
            # self._envisalinkclient.send_command("071", part + alarmcode)
        elif query.path == "/api/alarm/disarm":
            channel.pushok(json.dumps({"response" : "Request to disarm received"}))
            self._envisalinkclient.send_command("040", part + alarmcode)
        elif query.path == "/api/config/eventtimeago":
            channel.pushok(json.dumps({"eventtimeago" : str(self._config.EVENTTIMEAGO)}))
        elif query.path == "/img/glyphicons-halflings.png":
            channel.pushfile("glyphicons-halflings.png")
        elif query.path == "/img/glyphicons-halflings-white.png":
            channel.pushfile("glyphicons-halflings-white.png")
        elif query.path == "/favicon.ico":
            channel.pushfile("favicon.ico")
        else:
            if len(query.path.split("/")) == 2:
                try:
                    with open(sys.path[0] + os.sep + "ext" + os.sep + query.path.split("/")[1]) as f:
                        f.close()
                        channel.pushfile(query.path.split("/")[1])
                except IOError as e:
                    print("I/O error({0}): {1}".format(e.errno, e.strerror))
                    channel.pushstatus(404, "Not found")
                    channel.push("Content-type: text/html\r\n")
                    channel.push("File not found")
                    channel.push("\r\n")
            else:
                if (config.LOGURLREQUESTS):
                    alarmserver_logger("Invalid file requested")

                channel.pushstatus(404, "Not found")
                channel.push("Content-type: text/html\r\n")
                channel.push("\r\n")

class ProxyChannel(asynchat.async_chat):
    def __init__(self, server, proxypass, sock, addr):
        asynchat.async_chat.__init__(self, sock)
        self.server = server
        self.set_terminator(b"\r\n")
        self._buffer = []
        self._server = server
        self._clientMD5 = hashlib.md5(str(addr)).hexdigest()
        self._straddr = str(addr)
        self._proxypass = proxypass
        self._authenticated = False

        self.send_command("5053")

    def collect_incoming_data(self, data):
        # Append incoming data to the buffer
        self._buffer.append(data.decode("utf-8"))

    def found_terminator(self):
        line = "".join(self._buffer)
        self._buffer = []
        self.handle_line(line)

    def handle_line(self, line):
        alarmserver_logger("PROXY REQ < "+line)
        if self._authenticated == True:
            self._server._envisalinkclient.send_command(line, "", False)
        else:
            self.send_command("500005")
            expectedstring = "005" + self._proxypass + get_checksum("005", self._proxypass)
            if line == expectedstring:
                alarmserver_logger("Proxy User Authenticated")
                CONNECTEDCLIENTS[self._straddr]=self
                self._authenticated = True
                self.send_command("5051")
            else:
                alarmserver_logger("Proxy User Authentication failed")
                self.send_command("5050")
                self.close()

    def send_command(self, data, checksum = True):
        if checksum == True:
            to_send = data+get_checksum(data, "")+"\r\n"
        else:
            to_send = data+"\r\n"

        self.push(to_send.encode("utf-8"))

    def handle_close(self):
        alarmserver_logger("Proxy connection from %s closed" % self._straddr)
        if self._straddr in CONNECTEDCLIENTS: del CONNECTEDCLIENTS[self._straddr]
        self.close()

    def handle_error(self):
        alarmserver_logger("Proxy connection from %s errored" % self._straddr)
        if self._straddr in CONNECTEDCLIENTS: del CONNECTEDCLIENTS[self._straddr]
        self.close()

class EnvisalinkProxy(asyncore.dispatcher):
    def __init__(self, config, server):
        self._config = config
        if self._config.ENABLEPROXY == False:
            return

        asyncore.dispatcher.__init__(self)
        self.create_socket()
        self.set_reuse_addr()
        alarmserver_logger("Envisalink Proxy Started")

        self.bind(("", self._config.ENVISALINKPROXYPORT))
        self.listen(5)

    def handle_accept(self):
        pair = self.accept()
        if pair is None:
            pass
        else:
            sock, addr = pair
            alarmserver_logger("Incoming proxy connection from %s" % repr(addr))
            handler = ProxyChannel(server, self._config.ENVISALINKPROXYPASS, sock, addr)


def main(argv):
    try:
      opts, args = getopt.getopt(argv, "hc:", ["help", "config="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-c", "--config"):
            global conffile
            conffile = arg


if __name__=="__main__":
    cfg_file="alarmserver.cfg"
    main(sys.argv[1:])
    
    pathname = os.path.dirname(sys.argv[0])
    scriptpath = os.path.abspath(pathname)
    conffile = os.path.join(scriptpath,cfg_file)
    
    if os.path.exists(conffile):
        config = AlarmServerConfig(conffile)
        print(("Using configuration file %s" % conffile))
    
        if LOGTOFILE:
            outfile_handler = RotatingFileHandler(config.LOGFILE, mode="a", maxBytes=(config.LOGMAXSIZE), backupCount=config.LOGMAXBACKUPS)
            outfile = logging.getLogger()
            outfile.setLevel(logging.INFO)
            outfile.addHandler(outfile_handler)
            print(("Writing logfile to %s" % config.LOGFILE))

        alarmserver_logger("Alarm Server Starting...")
        alarmserver_logger("Currently Supporting Envisalink 2DS/3/4 only")
        alarmserver_logger("Tested on a DSC PC1616 + EVL-3")
        alarmserver_logger("and on a DSC PC1832 + EVL-2DS")
        alarmserver_logger("and on a DSC PC1832 v4.6 + EVL-4")
        alarmserver_logger("and on a DSC PC1864 v4.6 + EVL-3")

        DeviceSetup(config)
        
        try:
            server = AlarmServer(config)
        except:
            alarmserver_logger("Shutting down server due to errors.")
            sys.exit()

        proxy = EnvisalinkProxy(config, server)

        try:
            while True:
                asyncore.loop(timeout=2, count=1)
                # insert scheduling code here.
        except KeyboardInterrupt:
            print("Crtl+C pressed.")
            alarmserver_logger("Server interrupted by Ctrl+C.")
            shutdown_server(server)
        else:
            shutdown_server(server)
    else:
        print("Could not find configuration file %s" % confile)

def shutdown_server(server):
    alarmserver_logger("Shutting down server.")
    server.shutdown(socket.SHUT_RDWR) 
    server.close()
    sys.exit()