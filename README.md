# venus.RadioTemperature v1.0.4
Service to integrate a list of radio temperature sensors using rtl_433 binary. it can also fetch weather conditions from wunderground and openweather providers.


### Refrences
* [Venus Wiki](https://github.com/victronenergy/venus/wiki/dbus#temperature)
* [RTL 433](https://github.com/merbanan/rtl_433)

The Python script subscribes to a MQTT Broker and parses temperature and humidity data published by the RTL_433 script. These will send the values to dbus.
The script can create a special device fetching weather data from online providers (wunderground and openweather)


### Configuration

* #### Manual
  See config.sample.ini and amend for your own needs. Copy to `/data/conf` as `radio_temperature.config.ini`
    - In `[Setup]` set `debug` to enable debug level on logs, `gps` is your gps device to get your current position, `æggregate` = true will aggreagate data for outddor sensors with the online device
    - In `MQTTBroker` configure your MQQT broker, default is the Venus OS MQTT broker (127.0.0.1)
    - In `Online` configure the online weather provider to fetch weather information of your current position (you need an api key from the provider)
    - In `[Devices]` section you can specify all your radio devices
      - device_name = model,channel,topic,temparature json field, type
  
  
   **IMPORTANT**: configure `/data/conf/rtl.conf` for your needs - [RTL 433](https://github.com/merbanan/rtl_433)

### Installation

* #### SetupHelper
    1. install [SetupHelper](https://github.com/kwindrem/SetupHelper)
    2. enter `Package Manager` in Settings
    3. Enter `Inactive Packages`
    4. on `new` enter the following:
        - `package name` -> `RadioTemperature`
        - `GitHub user` -> `mebitek`
        - `GitHub branch or tag` -> `master`
    5. go to `Active packages` and click on `RadioTemperature`
        - click on `download` -> `proceed`
        - click on `install` -> `proceed`

| velib_pyhton available [here](https://github.com/victronenergy/velib_python/tree/master)

### Debugging
You can turn debug off on `config.ini` -> `debug=false`

The log you find in /var/log/RadioTemperature

`tail -f -n 200 /data/log/RadioTemperature/current`

You can check the status of the service with svstat:

`svstat /service/RadioTemperature`

It will show something like this:

`/service/RadioTemperature: up (pid 10078) 325 seconds`

If the number of seconds is always 0 or 1 or any other small number, it means that the service crashes and gets restarted all the time.

When you think that the script crashes, start it directly from the command line:

`python /data/RadioTemperature/RadioTemperature.py`

and see if it throws any error messages.


### Hardware

Tested with:
- Oregon Scientific THFR 810
- Thermopro TX2C
