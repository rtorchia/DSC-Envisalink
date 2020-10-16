/**
 *  DSC Away Panel
 *
 *  Author: Ralph Torchia
 *  Original Code By: Jordan <jordan@xeron.cc>, Rob Fisher <robfish@att.net>, Carlos Santiago <carloss66@gmail.com>, JTT <aesystems@gmail.com>
 *  Date: 2020-10-14
 */

metadata {
  definition (
    name: "DSC Away Panel",
    author: "Ralph Torchia",
    namespace: 'rtorchia',
    ocfDeviceType: "oic.d.securitypanel",
    mnmn: "SmartThingsCommunity",
    vid: "b5b2726f-6db4-3759-b10f-7b279b8724e1"
  )
  
  {
    capability "Switch"
    capability "Refresh"
    capability "pizzafiber16443.partitionStatus"
    capability "pizzafiber16443.partitionCommands"
    capability "Security System"
  }

  tiles {}

}

def partition(String state, String partition, Map parameters) {
  // state will be a valid state for the panel (ready, notready, armed, etc)
  // partition will be a partition number, for most users this will always be 1

  log.debug "Partition: ${state} for partition: ${partition}"

  def onList = ['alarm','away','entrydelay','exitdelay','instantaway']

  def chimeList = ['chime','nochime']

  def troubleMap = [
    'trouble':"detected",
    'restore':"clear",
  ]
  
  def altState = ""
  altState=getPrettyName().get(state)

  if (onList.contains(state)) {
    sendEvent (name: "switch", value: "on")
  } else if (!(chimeList.contains(state) || troubleMap[state] || state.startsWith('led') || state.startsWith('key'))) {
    sendEvent (name: "switch", value: "off")
  }

  if (troubleMap[state]) {
    def troubleState = troubleMap."${state}"
    // Send trouble event
    //sendEvent (name: "troubleStatus", value: "${troubleState}")
    sendEvent (name: "partitionStatus", value: "Trouble: ${troubleState}")
  } else if (chimeList.contains(state)) {
    // Send chime event
    sendEvent (name: "chime", value: "${state}")
  } else if (state.startsWith('led')) {
    def flash = (state.startsWith('ledflash')) ? 'flash ' : ''
    for (p in parameters) {
      //sendEvent (name: "led${p.key}", value: "${flash}${p.value}")
    }
  } else if (state.startsWith('key')) {
    def name = state.minus('alarm').minus('restore')
    def value = state.replaceAll(/.*(alarm|restore)/, '$1')
    //sendEvent (name: "${name}", value: "${value}")
  } else {
    // Send final event
    sendEvent (name: "status", value: "${state}")
    sendEvent (name: "partitionStatus", value: "${altState}")
    sendEvent (name: "partitionCommand", value: "Select command", descriptionText: "${state}")
  }
}

/* Start of ST Security System */
//arm away switch on
def on() {
  log.debug "Received on() for armedAway"
  sendEvent(name: "securitySystemStatus", value: "armedAway")
  sendPartitionCommand("away")
}
//disarm switch off
def off() {
  log.debug "Received off() for disarmed"
  sendEvent(name: "securitySystemStatus", value: "disarmed")
  sendPartitionCommand("disarm")
}

def armStay(evt) {
  log.debug "triggered armStay(${evt.value})"
  sendEvent(name: "switch", value: "on")
  sendEvent(name: "securitySystemStatus", value: "armedStay")
}
def armAway(evt) {
  log.debug "triggered armAway(${evt.value})"
  sendEvent(name: "switch", value: "on")
  sendEvent(name: "securitySystemStatus", value: "armedAway")
}
def disarm() {
  log.debug "triggered disarm()"
	sendEvent(name: "switch", value: "off")
  sendEvent(name: "securitySystemStatus", value: "disarmed")
  parent.sendUrl("disarm?part=${device.deviceNetworkId[-1]}")
}
/* End of ST Security System */

def away() {
  parent.sendUrl("arm?part=${device.deviceNetworkId[-1]}")
}

def autobypass() {
  parent.autoBypass()
}

def bypassoff() {
  parent.sendUrl("bypass?zone=0&part=${device.deviceNetworkId[-1]}")
}

def instant() {
  parent.sendUrl("toggleinstant?part=${device.deviceNetworkId[-1]}")
}

def night() {
  parent.sendUrl("togglenight?part=${device.deviceNetworkId[-1]}")
}

def nokey() {
  sendEvent (name: "key", value: "nokey")
}

def key() {
  sendEvent (name: "key", value: "key")
}

def keyfire() {
  if ("${device.currentValue("key")}" == 'key') {
    parent.sendUrl('panic?type=1')
  }
}

def keyaux() {
  if ("${device.currentValue("key")}" == 'key') {
    parent.sendUrl('panic?type=2')
  }
}

def keypanic() {
  if ("${device.currentValue("key")}" == 'key') {
    parent.sendUrl('panic?type=3')
  }
}

def refresh() {
  parent.sendUrl('refresh')
}

def reset() {
  parent.sendUrl("reset?part=${device.deviceNetworkId[-1]}")
}

def stay() {
  parent.sendUrl("stayarm?part=${device.deviceNetworkId[-1]}")
}

def togglechime() {
  parent.sendUrl("togglechime?part=${device.deviceNetworkId[-1]}")
}

def setPartitionCommand(String state) {
  log.debug "Processing command: ${state}"
  sendPartitionCommand(state)
}

def sendPartitionCommand(String state) {
  def altState = ""
  altState=getPrettyName().get(state)
  
  sendEvent (name: "partitionStatus", value: "${altState}")
  sendEvent (name: "partitionCommand", value: "${state}", descriptionText: "Command: ${state}")
      
  if (state =="away") { away() }
  else if (state == "autobypass") { autobypass() }
  else if (state == "bypassoff") { bypassoff() }
  else if (state == "disarm") { disarm() }
  else if (state == "instant") { instant() }
  else if (state == "night") { night() }
  else if (state == "nokey") { nokey () }
  else if (state == "key") { key() }
  else if (state == "keyfire") { keyfire() }
  else if (state == "keyaux") { keyaux() }
  else if (state == "keypanic") { keypanic() }
  else if (state == "reset") { reset() }
  else if (state == "stay") { stay() }
  else if (state == "chime") { togglechime() }
}

def getPrettyName() {
    return [
    ready: "Ready",
    forceready: "Ready",
    notready: "Not Ready",
    stay: "Armed Stay",
    away: "Armed Away",
    alarmcleared: "Alarm Cleared",
    instant: "Armed Instant",
    night: "Armed Night",
    disarm: "Disarming",
    exitdelay: "Exit Delay",
    entrydelay: "Entry Delay",
    chime: "Toggling Chime",
    bypassoff: "Sending Bypass Off",
    keyfire: "Sending Fire Alert",
    keyaux: "Sending Aux Alert",
    keypanic: "Sending Panic Alert"
	]
}    
