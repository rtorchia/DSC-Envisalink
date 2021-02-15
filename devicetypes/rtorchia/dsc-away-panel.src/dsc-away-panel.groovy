/**
 *  DSC Away Panel
 *
 *  Author: Ralph Torchia
 *  Original Code By: Jordan <jordan@xeron.cc>, Rob Fisher <robfish@att.net>, Carlos Santiago <carloss66@gmail.com>, JTT <aesystems@gmail.com>
 *  Date: 2021-02-13
 */

metadata {
  definition (
    name: 'DSC Away Panel',
    author: 'Ralph Torchia',
    namespace: 'rtorchia',
    //ocfDeviceType: 'oic.d.securitypanel',
    ocfDeviceType: 'oic.d.smartlock',
    deviceTypeId: 'SecurityPanel',
    mnmn: 'SmartThingsCommunity',
    vid: 'fb4dd121-56ac-35dc-a835-e4b14960da35',
    cstHandler: true
  )
  
  {
    capability 'Switch'
    capability 'pizzafiber16443.partitionStatus'
    capability 'pizzafiber16443.partitionCommands'
    capability 'Security System'
    capability 'Refresh'
  }

  tiles {}

}

def partition(String evt, String partition, Map parameters) {
  // evt will be a valid event for the panel (ready, notready, armed, etc)
  // partition will be a partition number, for most users this will always be 1

  log.debug "Partition: ${evt} for partition: ${partition}"

  def onList = ['alarm','away','entrydelay','exitdelay','instantaway']

  def chimeList = ['chime','nochime']

  def troubleMap = [
    'trouble': 'detected',
    'restore': 'clear',
  ]
  
  if (onList.contains(evt)) {
    sendEvent (name: "switch", value: "on")
    //sendEvent (name: "partitionStatus", value: "${evt}")
  } else if (!(chimeList.contains(evt) || troubleMap[evt] || evt.startsWith('led') || evt.startsWith('key'))) {
    sendEvent (name: "switch", value: "off")
    //sendEvent (name: "partitionStatus", value: "disarm")
  }

  if (troubleMap[evt]) {
    def troubleState = troubleMap."${evt}"
    // Send trouble event
    //sendEvent (name: "troubleStatus", value: "${troubleState}")
    sendEvent (name: "partitionStatus", value: "Trouble: ${troubleState}")
  } else if (chimeList.contains(evt)) {
    // Send chime event
    sendEvent (name: "chime", value: "${evt}")
  } else if (evt.startsWith('led')) {
    def flash = (evt.startsWith('ledflash')) ? 'flash ' : ''
    for (p in parameters) {
      //sendEvent (name: "led${p.key}", value: "${flash}${p.value}")
    }
  } else if (evt.startsWith('key')) {
    def name = evt.minus('alarm').minus('restore')
    def value = evt.replaceAll(/.*(alarm|restore)/, '$1')
    //sendEvent (name: "${name}", value: "${value}")
  } else {
    // Send final event
    sendEvent (name: "partitionStatus", value: "${evt}")
    sendEvent (name: "partitionCommand", value: "Select command", descriptionText: "${evt}")
  }
}

def installed() { state.sendurl = true }

//arm away = switch on
def on() {
  log.debug "Triggered on() for arm away"
  away()
}

def armAway(evt) {
  log.debug "Triggered armAway()"
  away()
}

//disarm = switch off
def off() {
  log.debug "Triggered off() for disarm"
  disarm()
}

def disarm() {
  log.debug "Triggered disarm()"
  parent.sendUrl("disarm?part=${device.deviceNetworkId[-1]}")
}

def away() {
  parent.sendUrl("arm?part=${device.deviceNetworkId[-1]}")
}

def stay() {
  if (state.sendurl==true) {
    state.sendurl = false
    log.debug "Triggered stay()"
    parent.sendUrl("stayarm?part=${device.deviceNetworkId[-1]}")
    state.sendurl = true
  }
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

def togglechime() {
  parent.sendUrl("togglechime?part=${device.deviceNetworkId[-1]}")
}

def setPartitionCommand(String evt) {
  log.debug "Processing command: ${evt}"
  
  sendEvent (name: "partitionStatus", value: "${evt}")
  sendEvent (name: "partitionCommand", value: "${evt}", descriptionText: "Command: ${evt}")
      
  if (evt =='away') { away() }
  else if (evt == 'autobypass') { autobypass() }
  else if (evt == 'bypassoff') { bypassoff() }
  else if (evt == 'disarm') { disarm() }
  else if (evt == 'instant') { instant() }
  else if (evt == 'night') { night() }
  else if (evt == 'nokey') { nokey () }
  else if (evt == 'key') { key() }
  else if (evt == 'keyfire') { keyfire() }
  else if (evt == 'keyaux') { keyaux() }
  else if (evt == 'keypanic') { keypanic() }
  else if (evt == 'reset') { reset() }
  else if (evt == 'stay') { stay() }
  else if (evt == 'chime') { togglechime() }
}
