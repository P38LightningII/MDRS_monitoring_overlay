import network
import socket
import time
from machine import Pin as pin
import securityInfo
import uasyncio as asyncio

def read_txt(path):
    with open(path, 'r') as input_file:
        data = input_file.read()
    return data

def connect_to_network():
    wlan = network.WLAN(network.STA_IF)
    wlan.disconnect()
    wlan.active(True)
    # wlan.config(pm = 0xa11140) # Disable power-save mode
    
    wlan.disconnect()
    wlan.connect(securityInfo.ssid, securityInfo.wifi_password)

    print("Finding Connection, timeout in 30 seconds")
    print("Network ssid: " + securityInfo.ssid)
    print("Password: " + securityInfo.wifi_password)
    print("waiting for connection...")
    max_wait = 30
    while max_wait > 0:
        if wlan.status() == 3:
            break
        max_wait -= 1
        time.sleep(1)

    if wlan.status() != 3:
        print("wlan.status() == {0}".format(wlan.status()))
        raise RuntimeError('network connection failed')
    else:
        print("Connected to {}".format(securityInfo.ssid))
        status = wlan.ifconfig()
        print('ip == ' + status[0])
    

def load_html(path = "txtLog.html", args = []):
    htmlFile = open(path, "r")
    html = htmlFile.read()
    htmlFile.close()
    for file in args:
        file_data = read_txt(file[1])
        html = html.replace(file[0], file_data)
    return html

async def serve_client(reader, writer):
    print("Client connected")

    # no need to get reader input, oly displaying static page for now

    request_line = await reader.readline()
    correct_password = str(request_line).find(securityInfo.website_password)
    # We are not interested in HTTP request headers, skip them
    while await reader.readline() != b"\r\n":
        pass
    if correct_password >= 0:
        response = load_html('txtLog.html', [['co2_data', 'CO2_log.csv'],
                                            ['voc_data', 'VOC_log.csv'],
                                            ['temp_data', 'Temp_log.csv'],
                                            ['pm_data', 'PM2.5_log.csv']])
    else:
        response = response = load_html('passwordRequest.html')

    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(response)
    
    await writer.drain()
    await writer.wait_closed()
    print("Client disconnected")

async def main():
    connect_to_network()
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))

    is_logging_data = True
    try:
        if is_logging_data:
            try:
                import collectSensorData
            except:
                raise ValueError("Sensor reading python file not found on pi, make sure it's copied over")
    
            print("Imports and pin setup successful")
            file_names = collectSensorData.file_names_setup()
            
            button_reading_pin = machine.Pin(6, machine.Pin.IN, machine.Pin.PULL_DOWN)
            collectSensorData.button_interrupt_setup(button_reading_pin)

            last_log_time = -1000*60*60 # last log was 1 hour ago in ms
            while True:
                if (time.ticks_ms() - last_log_time) > (1000*60*60): # log values if last log was 1 hour ago
                    collectSensorData.record_values(file_names)
                    last_log_time = time.ticks_ms()
                await asyncio.sleep(0.25)
            
        else:
            while True:
                await asyncio.sleep(0.25)

    except KeyboardInterrupt:
        print("Successfully exited via keyboard")

try: 
    asyncio.run(main())
finally:
    asyncio.new_event_loop()

