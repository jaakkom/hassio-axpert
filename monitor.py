#!/usr/bin/python

import time
import os
import crcmod.predefined
from binascii import unhexlify
import paho.mqtt.client as mqtt
import serial
from random import randint
import json

battery_types = {'0': 'AGM', '1': 'Flooded', '2': 'User', '3': 'lithium'}
voltage_ranges = {'0': 'Appliance', '1': 'UPS'}
output_sources = {'0': 'utility', '1': 'solar', '2': 'battery'}
charger_sources = {'0': 'utility first', '1': 'solar first', '2': 'solar + utility', '3': 'solar only'}
machine_types = {'00': 'Grid tie', '01': 'Off Grid', '10': 'Hybrid'}
topologies = {'0': 'transformerless', '1': 'transformer'}
output_modes = {'0': 'single machine output', '1': 'parallel output', '2': 'Phase 1 of 3 Phase output', '3': 'Phase 2 of 3 Phase output', '4': 'Phase 3 of 3 Phase output'}
pv_ok_conditions = {'0': 'As long as one unit of inverters has connect PV, parallel system will consider PV OK', '1': 'Only All of inverters have connect PV, parallel system will consider PV OK'}
pv_power_balance = {'0': 'PV input max current will be the max charged current', '1': 'PV input max power will be the sum of the max charged power and loads power'}
modes = {'P': 'PowerOnMode', 'S': 'StandByMode', 'L': 'LineMode', 'B': 'BatteryMode', 'F': 'FaultMode'}

def connect():
    global client
    client = mqtt.Client(client_id=os.environ['MQTT_CLIENT_ID'])
    client.username_pw_set(os.environ['MQTT_USER'], os.environ['MQTT_PASS'])
    client.connect(os.environ['MQTT_SERVER'])
    print(f"Connected to MQTT server {os.environ['MQTT_SERVER']}")

def serial_command(command):
    try:
        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
        command_bytes = command.encode('utf-8')
        command_crc_hex = hex(xmodem_crc_func(command_bytes)).replace('0x', '')
        command_crc = command_bytes + unhexlify(command_crc_hex.encode('utf-8')) + b'\x0d'

        with serial.Serial(os.environ['DEVICE'], 2400, timeout=4) as ser:
            ser.write(command_crc)
            response = ser.read_until(b'\r').strip()
        
        response = response.decode('utf-8', errors='ignore')

        if len(response) == 0 or response[0] != '(' or 'NAKss' in response:
            raise Exception('Invalid response')

        return response[1:-2]

    except Exception as e:
        print(f"Error reading inverter: {e}")
        time.sleep(0.1)
        connect()
        return serial_command(command)

def get_mode():
    try:
        response = serial_command('QMOD')
        mode = response[0]
        data = json.dumps({"Mode": modes.get(mode, "Unknown")})
    except Exception as e:
        print(f"Error parsing inverter data: {e}")
        return ''
    return data

def get_parallel_data():
    try:
        response = serial_command('QPGS0')
        nums = response.split(' ')
        if len(nums) < 27:
            return ''

        data = '{'
        data += '"Gridmode":1' if nums[2] == 'L' else '"Gridmode":0'
        data += ',"SerialNumber": ' + str(int(nums[1]))
        data += ',"BatteryChargingCurrent": ' + str(int(nums[12]))
        data += ',"BatteryDischargeCurrent": ' + str(int(nums[26]))
        data += ',"TotalChargingCurrent": ' + str(int(nums[15]))
        data += ',"GridVoltage": ' + str(float(nums[4]))
        data += ',"GridFrequency": ' + str(float(nums[5]))
        data += ',"OutputVoltage": ' + str(float(nums[6]))
        data += ',"OutputFrequency": ' + str(float(nums[7]))
        data += ',"OutputAparentPower": ' + str(int(nums[8]))
        data += ',"OutputActivePower": ' + str(int(nums[9]))
        data += ',"LoadPercentage": ' + str(int(nums[10]))
        data += ',"BatteryVoltage": ' + str(float(nums[11]))
        data += ',"BatteryCapacity": ' + str(float(nums[13]))
        data += ',"PvInputVoltage": ' + str(float(nums[14]))
        data += ',"TotalAcOutputApparentPower": ' + str(int(nums[16]))
        data += ',"TotalAcOutputActivePower": ' + str(int(nums[17]))
        data += ',"TotalAcOutputPercentage": ' + str(int(nums[18]))
        data += ',"OutputMode": ' + str(int(nums[20]))
        data += ',"ChargerSourcePriority": ' + str(int(nums[21]))
        data += ',"MaxChargeCurrent": ' + str(int(nums[22]))
        data += ',"MaxChargerRange": ' + str(int(nums[23]))
        data += ',"MaxAcChargerCurrent": ' + str(int(nums[24]))
        data += ',"PvInputCurrentForBattery": ' + str(int(nums[25]))
        data += ',"Solarmode":1' if nums[2] == 'B' else ',"Solarmode":0'
        data += '}'
        return data
    except Exception as e:
        print(f"Error parsing inverter data: {e}")
        return ''

def get_data():
    try:
        response = serial_command('QPIGS')
        nums = response.split(' ')
        if len(nums) < 21:
            return ''

        data = '{'
        data += '"BusVoltage":' + str(float(nums[2]))
        data += ',"InverterHeatsinkTemperature":' + str(float(nums[11]))
        data += ',"BatteryVoltageFromScc":' + str(float(nums[8]))
        data += ',"PvInputCurrent":' + str(float(nums[12]))
        data += ',"PvInputVoltage":' + str(float(nums[13]))
        data += ',"PvInputPower":' + str(int(nums[19]))
        #data += ',"BatteryChargingCurrent": ' + str(int(nums[9]))
        #data += ',"BatteryDischargeCurrent":' + str(int(nums[15]))
        #data += ',"DeviceStatus":"' + nums[16] + '"'
        data += '}'
        return data
    except Exception as e:
        print(f"Error parsing inverter data: {e}")
        return ''

def get_settings():
    try:
        response = serial_command('QPIRI')
        nums = response.split(' ')
        if len(nums) < 21:
            return ''

        data = '{'
        #data += '"AcInputVoltage":' + str(float(nums[0]))
        #data += ',"AcInputCurrent":' + str(float(nums[1]))
        #data += ',"AcOutputVoltage":' + str(float(nums[2]))
        #data += ',"AcOutputFrequency":' + str(float(nums[3]))
        #data += ',"AcOutputCurrent":' + str(float(nums[4]))
        #data += ',"AcOutputApparentPower":' + str(int(nums[5]))
        #data += ',"AcOutputActivePower":' + str(int(nums[6]))
        #data += ',"BatteryVoltage":' + str(float(nums[7]))
        #data += ',"BatteryRechargeVoltage":' + str(float(nums[8]))
        #data += ',"BatteryUnderVoltage":' + str(float(nums[9]))
        #data += ',"BatteryBulkVoltage":' + str(float(nums[10]))
        #data += ',"BatteryFloatVoltage":' + str(float(nums[11]))
        data += '"BatteryType":"' + battery_types.get(nums[12], "Unknown") + '"'
        #data += ',"MaxAcChargingCurrent":' + str(int(nums[13]))
        #data += ',"MaxChargingCurrent":' + str(int(nums[14]))
        #data += ',"InputVoltageRange":"' + voltage_ranges.get(nums[15], "Unknown") + '"'
        data += ',"OutputSourcePriority":"' + output_sources.get(nums[16], "Unknown") + '"'
        data += ',"ChargerSourcePriority":"' + charger_sources.get(nums[17], "Unknown") + '"'
        #data += ',"MaxParallelUnits":' + str(int(nums[18]))
        #data += ',"MachineType":"' + machine_types.get(nums[19], "Unknown") + '"'
        #data += ',"Topology":"' + topologies.get(nums[20], "Unknown") + '"'
        #data += ',"OutputMode":"' + output_modes.get(nums[21], "Unknown") + '"'
        #data += ',"BatteryRedischargeVoltage":' + str(float(nums[22]))
        #data += ',"PvOkCondition":"' + pv_ok_conditions.get(nums[23], "Unknown") + '"'
        #data += ',"PvPowerBalance":"' + pv_power_balance.get(nums[24], "Unknown") + '"'
        data += '}'
        return data
    except Exception as e:
        print(f"Error parsing inverter data: {e}")
        return ''

def send_data(data, topic):
    try:
        print(f"Publishing to {topic}: {data}")
        client.publish(topic, data, qos=0, retain=True)
    except Exception as e:
        print(f"Error sending data to MQTT: {e}")
        return 0
    return 1

def publish_discovery(serial_number):
    base_topic = os.environ['MQTT_DISCOVERY_PREFIX']
    device_name = os.environ['MQTT_DEVICE_NAME']
    
    discovery_data = {
        "identifiers": [serial_number],
        "manufacturer": "Your Inverter Manufacturer",
        "model": "Your Inverter Model",
        "name": device_name,
        "sw_version": "1.0"
    }

    sensors = {
        "BusVoltage": {
            "name": "Bus Voltage",
            "unit_of_measurement": "V",
            "device_class": "voltage"
        },
        "InverterHeatsinkTemperature": {
            "name": "Inverter Heatsink Temperature",
            "unit_of_measurement": "°C",
            "device_class": "temperature"
        },
        "BatteryVoltageFromScc": {
            "name": "Battery Voltage from SCC",
            "unit_of_measurement": "V",
            "device_class": "voltage"
        },
        "PvInputCurrent": {
            "name": "PV Input Current",
            "unit_of_measurement": "A",
            "device_class": "current"
        },
        "PvInputVoltage": {
            "name": "PV Input Voltage",
            "unit_of_measurement": "V",
            "device_class": "voltage"
        },
        "PvInputPower": {
            "name": "PV Input Power",
            "unit_of_measurement": "W",
            "device_class": "power"
        }
    }

    for sensor, config in sensors.items():
        config["state_topic"] = os.environ['MQTT_TOPIC'].replace('{sn}', serial_number)
        config["value_template"] = f"{{{{ value_json.{sensor} }}}}"
        config["unique_id"] = f"{serial_number}_{sensor.lower()}"
        config["device"] = discovery_data

        discovery_topic = f"{base_topic}/sensor/{serial_number}/{sensor.lower()}/config"
        client.publish(discovery_topic, json.dumps(config), qos=0, retain=True)

def main():
    time.sleep(randint(0, 5))  # Stagger start times for parallel streams
    connect()

    try:
        serial_number = serial_command('QID')
        print(f"Reading from inverter {serial_number}")
        publish_discovery(serial_number)
    except Exception as e:
        print(f"Error obtaining serial number: {e}")
        return

    while True:
        try:
            data = get_data()
            if data:
                send_data(data, os.environ['MQTT_TOPIC'].replace('{sn}', serial_number))
            time.sleep(1)

            data = get_settings()
            if data:
                send_data(data, os.environ['MQTT_TOPIC_SETTINGS'])
            time.sleep(4)
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(10)  # Delay before retrying to avoid continuous strain

if __name__ == '__main__':
    main()
