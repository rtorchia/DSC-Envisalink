/*
 *  DSC Zone Motion Device
 *
 *  Author: Ralph Torchia
 *  Originally By: Jordan <jordan@xeron.cc>, Matt Martz <matt.martz@gmail.com>, Kent Holloway <drizit@gmail.com>
 *  Date: 2020-10-07
 */

metadata {
  definition (
    name: "DSC Zone Motion",
    author: "Ralph Torchia",
    namespace: 'dsc',
    mnmn: "SmartThingsCommunity",
    vid: "621df660-ac84-3683-b76c-02df10c8bd06"
  )
  {
    capability "Motion Sensor"
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
      tileAttribute ("device.motion", key: "PRIMARY_CONTROL") {
        attributeState "active", label:'motion', icon:"st.motion.motion.active", backgroundColor:"#53a7c0"
        attributeState "inactive", label:'no motion', icon:"st.motion.motion.inactive", backgroundColor:"#ffffff"
        attributeState "alarm", label:'ALARM', icon:"st.motion.motion.active", backgroundColor:"#ff0000"
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
    // Since this is a motion device we need to convert the values to match the device capabilities
    // Alarming isn't a valid option for this capability, but we map this here anyway, so you can more easily tell which device
    // is alarming from the "things" page.
    def motionMap = [
     'open':"active",
     'closed':"inactive",
     'noalarm':"inactive",
     'alarm':"alarm"
    ]

    sendEvent (name: "motion", value: "${motionMap[state]}")
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
