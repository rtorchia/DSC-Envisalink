/*
 *  DSC Zone Contact Device
 *
 *  Author: Ralph Torchia
 *  Originally By: Jordan <jordan@xeron.cc>, Matt Martz <matt.martz@gmail.com>, Kent Holloway <drizit@gmail.com>
 *  Date: 2021-03-08
 */

metadata {
    definition (
        name: 'DSC Zone Contact',
        author: 'Ralph Torchia',
        namespace: 'rtorchia',
        mnmn: 'SmartThingsCommunity',
        vid: 'a1dcac40-0e99-35d1-a9c8-0da98ae23fd8'
    )

    {
        capability 'Contact Sensor'
        capability 'Sensor'
        capability 'Alarm'
        capability 'pizzafiber16443.zoneBypass'
        capability 'pizzafiber16443.troubleStatus'
    }

    tiles {}  
}

// handle commands
def setZoneBypass(String evt) {
    def zone = device.deviceNetworkId.minus('dsczone')
    parent.sendUrl("bypass?zone=${zone}")
    sendEvent (name: "zoneBypass", value: "${evt}")
}

def zone(String state) {
    // state will be a valid state for a zone (open, closed)
    // zone will be a number for the zone
    log.debug "Zone: ${state}"

    def troubleList = ['fault', 'tamper', 'restore']

    def bypassList = ['on', 'off']

    def alarmMap = [
        'alarm': 'both',
        'noalarm': 'off'
    ]

    if (troubleList.contains(state)) {
        sendEvent (name: "troubleStatus", value: "${state}")
    } else if (bypassList.contains(state)) {
        sendEvent (name: "zoneBypass", value: "${state}")
    } else {
        // Send actual alarm state, if we have one
        if (alarmMap.containsKey(state)) {
            sendEvent (name: "alarm", value: "${alarmMap[state]}")
        } else {
            sendEvent (name: "alarm", value: "off")
        }
        // Alarming isn't a valid option for this capability, but we map this here anyway,
        // so you can more easily tell which device is alarming from the "things" page.
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
    sendEvent (name: "troubleStatus", value: "restore")
    sendEvent (name: "zoneBypass", value: "off")
    off()
}
