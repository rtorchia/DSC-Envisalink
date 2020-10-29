/**
 *  Security System Panel
 *  DSC Simple Away Panel
 *  Author: Ralph Torchia <ralphtorchia1@gmail.com>
 *  Date: 2020-10-25
 */

metadata {
	definition (
        name: "DSC Simple Away Panel",
        namespace: "rtorchia",
        author: "Ralph Torchia",
        vid: "e88671f1-1ca0-32ce-bfee-ae0c1136efc1",
        mnmn: "SmartThingsCommunity",
        cstHandler: true
    )
    {
        capability "Switch"
        capability "Security System"
 	}

	tiles {}
}

// parse events into attributes
def installed() {
    initialize()
}

def initialize() {
    sendEvent(name: "switch", value: "off")
    sendEvent(name: "securitySystemStatus", value: "disarmed")
    //sendEvent(name: "alarm", value: "off")
}

def armStay(evt) {
    log.debug "Triggered armStay(${evt.value})"
    def switchStatus = device.currentState("switch").value
    if (switchStatus == "off") {
      sendEvent(name: "switch", value: "on")
      //sendEvent(name: "securitySystemStatus", value: "armedStay")
    }
}

def armAway(evt) {
    log.debug "Triggered armAway(${evt.value})"
    def switchStatus = device.currentState("switch").value
    if (switchStatus == "off") {
      sendEvent(name: "switch", value: "on")
      //sendEvent(name: "securitySystemStatus", value: "armedAway")
    }
}

def disarm() {
    log.debug "Triggered disarm()"
    sendEvent(name: "switch", value: "off")
    sendEvent(name: "securitySystemStatus", value: "disarmed")
}

def on() {
    log.debug "Armimg (away) security system"
    sendEvent(name: "switch", value: "on")
    sendEvent(name: "securitySystemStatus", value: "armedAway")
}

def off() {
    log.debug "Disarming security system"
    sendEvent(name: "switch", value: "off")
    sendEvent(name: "securitySystemStatus", value: "disarmed")
}