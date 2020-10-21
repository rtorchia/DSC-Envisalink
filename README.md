# DSC-Envisalink

Allows a DSC security panel with Envisalink to integrate into SmartThings. Requires the use of Alarmserver running on any server, Envisalink module connected to a DSC security panel, and the SmartThings App.

This integration is mostly complete and working, but some items do not work as SmartThings still has issues with custom capabilities and switches.

## Setup Instructions

### Summary

* Install Python and AlarmServer on your server, and all required dependencies.
* Install SmartThings device handlers and smartapp in Groovy IDE, and turn on OAuth for DSC-Envisalink smartapp.
* From mobile device, install DSC-Envisalink SmartApp in SmartThings app, and retrieve the app id, access token and url base from the SmartApp.
* Edit _alarmserver.cfg_ on server.
* Edit DSC-Envisalink preferences on mobile device.
* Start AlarmServer on the server.

### Alarmserver Setup

1. Install and setup python 3.x on your server. (see https://www.python.org/)
   If using Windows, you can also install Python from the Microsoft Store (https://www.microsoft.com/store/productId/9MSSZTT1N39L)

2. Copy the contents of the alarmsever folder from github to your system. Make sure to install the python dependencies required for AlarmServer.

3. Edit the _alarmserver.cfg_ file and add in the OAuth/Access Code information to the _callback_url_app_id_ and _callbackurl_access_token_ values (see SmartThings and SmartApp Setup)
   Also adjust your zones/partitions at the bottom of the file, and all other information in the configuration file.

4. Start AlarmServer. Your devices should get created in SmartThings, and you should start seeing events pushed to them within a few moments on your mobile device.
   Don't forget to open port 8111 on the server's firewall!

### SmartThings Setup

1. From the SmartThings Grovvy IDE setup github integration.

2. Add a new github repository from the settings, with _rtorchia_ as owner, _DSC-Envisalink_ as name, and _master_ as branch.

3. Once you have setup this repo, you can easily add all the devices handlers and the smartapp from the _Update from repo_ button for each section. Be sure to check the _publish_ checkbox at the bottom right.

4. After the DSC-Envisalink SmartApp is installed in the IDE, find it in the list and select _Edit Properties_.

5. Click _Enable OAuth_ in Smart App" and save the changes.

### SmartApp Setup

1. On your mobile device, open the SmartThings app, go to the SmartApps section, and add/install DSC-Envisalink.

2. In the SmartApp preferences screen, scroll to the _Show SmartApp Token Info_. Copy this information and save it (You can email it to yourself). You will need this information for the _alarmserver.cfg_ file.

3. In your _alarmserver.cfg_ file, locate the following lines the app ID and access token:
   _callbackurl_app_id=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx_
   _callbackurl_access_token=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx_
   Additionally, you might want to set the _callbackurl_base_ line in the cfg file to whatever URL is output in the SmartApp Token info if the regular _https://graph.api.smartthings.com_ URL does not apply for you.

4. Edit the settings for the DSC-Envisalink SmartApp on your mobile, and fill in the IP address and Port number with the correct information for your system running alarmserver.

## Thanks!

Thanks goes out to the following people, without their previous work none of this would have been possible:
* juggie
* Ethomasii
* blacktirion
* Rob Fisher <robfish@att.net>
* Carlos Santiago <carloss66@gmail.com>
* JTT <aesystems@gmail.com>
* Donny K <donnyk+envisalink@gmail.com>
* Leaberry <leaberry@gmail.com>
* Kent Holloway <drizit@gmail.com>
* Matt Martz <matt.martz@gmail.com>
* Jordan <jordan@xeron.cc>
