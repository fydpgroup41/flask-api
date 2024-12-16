from flask import Flask, jsonify
import json
import csv
from pymodbus.client import ModbusSerialClient as ModbusSerialClient
import time

app = Flask(__name__)

# Function to read Modbus registers from the client
def read_registers(client, address, slave, quantity):
    try:
        data = client.read_holding_registers(address, quantity, slave=slave)
        if data.isError():
            print(f"Error reading registers: {data}")
            return None
        return data.registers
    except Exception as e:
        print(f"Modbus register error: {e}")
        return None

# Function to clean and process the data
def clean_data(data_array):
    for data in data_array:
        data[0] = data[0] / 10  # Voltage scaling
        data[1] = data[1] / 100  # Current scaling
        data[2] = data[2] / 1  # Active power scaling
        data[3] = data[3] / 1  # Reactive power scaling
        data[4] = data[4] / 1000  # Power factor scaling
        data[5] = data[5] / 100  # Frequency scaling
        power = data[0] * data[1] * data[2]  # Power calculation
        data.append(power)

if __name__ == "__main__":
    header = ['Voltage', 'Current', 'Active Power', 'Reactive Power', 'Power Factor', "Frequency", "Time", 'Power']

    app.run(debug=True)

# Parameters for Modbus serial connection
port = "COM5"
baudrate = 9600
stopbits = 1
bytesize = 8
parity = "E"
timeout = 30
retries = 5

# Start Modbus client
client = ModbusSerialClient(
    port=port,
    baudrate=baudrate,
    stopbits=stopbits,
    bytesize=bytesize,
    parity=parity,
    timeout=timeout,
    retries=retries
)

client.method = 'rtu'

if client.connect():
    print("Modbus client connected successfully.")
else:
    print("Failed to connect to Modbus client.")
    exit()

# Data collection
data = []
try:
    client.connect()
    start_time = time.time()
    while time.time() - start_time < 240:
        registers_data = read_registers(client, 0x0008, slave=11, quantity=6)
        if registers_data is not None:
            registers_data.append(time.time())
            data.append(registers_data)
        print(f"Registers data: {registers_data}")
        time.sleep(0.91)
except KeyboardInterrupt:
    print("Exiting due to user interruption.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if client.is_socket_open():
        client.close()
    clean_data(data)

    # Write data to JSON
    json_file_path = 'output_areeb.json'
    with open(json_file_path, 'w') as json_file:
        json.dump(data, json_file)

    # Write data to CSV
    csv_file_path = 'output_areeb.csv'
    with open(csv_file_path, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(header)
        for d in data:
            csv_writer.writerow(d)

# Flask API Routes
@app.route('/api/json-data', methods=['GET'])
def serve_json():
    try:
        with open(json_file_path, 'r') as file:
            json_data = json.load(file)
        return jsonify(json_data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/csv-data', methods=['GET'])
def serve_csv():
    try:
        df = pd.read_csv(csv_file_path)
        data = df.to_dict(orient='records')
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/')
def home():
    return "Welcome to the Live Flask API! Use /api/json-data or /api/csv-data to fetch data."

