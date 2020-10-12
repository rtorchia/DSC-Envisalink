/*
 *  DSC Zone Contact Device
 *
 *  Author: Ralph Torchia
 *  Originally By: Jordan <jordan@xeron.cc>, Matt Martz <matt.martz@gmail.com>, Kent Holloway <drizit@gmail.com>
 *  Date: 2020-10-07
 */

metadata {
  definition (
    name: "DSC Zone Contact",
    author: "Ralph Torchia",
    namespace: 'dsc',
    mnmn: "SmartThingsCommunity",
    vid: "4cf13940-90d0-34ed-95f9-67f7bc92c03c"
  )
  {
    capability "Contact Sensor"
    capability "Sensor"
    capability "Alarm"
    capability "pizzafiber16443.zoneBypass"
    capability "pizzafiber16443.troubleStatus"
    //capability "Momentary"
    
    attribute "bypass", "string"
    attribute "trouble", "string"

    command "zone"
    command "bypass"
    command "setZoneBypass"
  }
  
  //for old app
  tiles(scale: 2) {
    multiAttributeTile(name:"zone", type: "generic", width: 6, height: 4) {
      tileAttribute ("device.contact", key: "PRIMARY_CONTROL") {
        attributeState "open", label: '${name}', icon: "st.contact.contact.open", backgroundColor: "#ffa81e"
        attributeState "closed", label: '${name}', icon: "st.contact.contact.closed", backgroundColor: "#79b821"
        attributeState "alarm", label: 'ALARM', icon: "st.contact.contact.open", backgroundColor: "#ff0000"
      }
      tileAttribute ("device.trouble", key: "SECONDARY_CONTROL") {
        attributeState "restore", label: 'No Trouble', icon: "st.security.alarm.clear"
        attributeState "tamper", label: 'Tamper', icon: "st.security.alarm.alarm"
        attributeState "fault", label: 'Fault', icon: "st.security.alarm.alarm"
      }
    }
    standardTile("bypass", "device.bypass", width: 3, height: 2, title: "Bypass Status", decoration:"flat"){
      state "off", label: 'Enabled', action: "bypass", icon: "st.security.alarm.on"
      state "on", label: 'Bypassed', action: "bypass", icon: "st.security.alarm.off"
    }
    standardTile("alarm", "device.alarm", width: 3, height: 2, title: "Alarm Status", decoration: "flat"){
      state "off", label: 'No Alarm', icon: "st.security.alarm.off"
      state "both", label: 'ALARM', icon: "st.security.alarm.on"
    }

    main "zone"

    details(["zone", "bypass", "alarm"])
  }
}

// handle commands
def bypass() {
  def zone = device.deviceNetworkId.minus('dsczone')
  parent.sendUrl("bypass?zone=${zone}")
}
def setZoneBypass() {
  bypass()
  sendEvent (name: "zoneBypass", value: "on")
}

def zone(String state) {
  // state will be a valid state for a zone (open, closed)
  // zone will be a number for the zone
  log.debug "Zone: ${state}"

  //def troubleList = ['fault','tamper','restore']
  def troubleMap = [
    'restore': 'No Trouble',
    'tamper': 'Tamper',
    'fault': 'Fault'
  ]
  def bypassList = ['on','off']
  def alarmMap = [
    'alarm': "both",
    'noalarm': "off"
  ]

  if (troubleMap.containsKey(state)) {
    sendEvent (name: "trouble", value: "${state}")
    sendEvent (name: "troubleStatus", value: "${troubleMap[state]}")
  } else if (bypassList.contains(state)) {
    sendEvent (name: "bypass", value: "${state}")
    sendEvent (name: "zoneBypass", value: "${state}")
  } else {
    // Send actual alarm state, if we have one
    if (alarmMap.containsKey(state)) {
      sendEvent (name: "alarm", value: "${alarmMap[state]}")
    } else {
      sendEvent (name: "alarm", value: "off")
    }
    // Alarming isn't a valid option for this capability, but we map this here anyway, so you can more easily tell which device
    // is alarming from the "things" page.
    sendEvent (name: "contact", value: "${state.replaceAll('noalarm', 'closed')}")
  }
}

def updated() {
  //do nothing for now
}
def installed() {
  initialize()
}

//just reset if any button is pushed for now
def both() {
  sendEvent (name: "alarm", value: "off")
}
def off() {
  sendEvent (name: "alarm", value: "off")
}
def siren() {
  sendEvent (name: "alarm", value: "off")
}
def strobe() {
  sendEvent (name: "alarm", value: "off")
}

private initialize() {
	log.trace "Executing initialize()"
    //set default values
    sendEvent (name: "troubleStatus", value: "No Trouble")
    sendEvent (name: "zoneBypass", value: "off")
	off()
}