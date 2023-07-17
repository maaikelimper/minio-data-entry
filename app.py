from flask import Flask, render_template, request, jsonify
from minio import Minio, InvalidResponseError

import io

import time
import paho.mqtt.client as mqtt

app = Flask(__name__)

# MinIO configuration
MINIO_ENDPOINT = '172.17.0.1:9000'
MINIO_ACCESS_KEY = None
MINIO_SECRET_KEY = None
MINIO_BUCKET_NAME = 'wis2box-incoming'

# log to stdout
import sys
import logging
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.INFO)


# MQTT callback functions
def on_connect(client, userdata, flags, rc):
    app.logger.info(f"Connected with result code {rc}")
    # Subscribe to the desired topic
    client.subscribe("origin/#", qos=1)

def on_message(client, userdata, msg):
    # Handle received messages
    app.logger.info(f"Received message: {msg.payload.decode()}")

# Routes
@app.route('/test')
def test():
    return render_template('test.html')

# Routes
@app.route('/data_entry')
def data_entry():
    return render_template('data_entry.html')

# Routes
@app.route('/')
def index():
    return render_template('data_entry.html')

@app.route('/submit', methods=['POST'])
def submit():
    username = request.form['username']
    password = request.form['password']

    year = request.form['year']
    month = request.form['month']

    filename = f'data-{year}{month}.txt'

    data = request.form['data']

    # Set the MinIO access keys
    global MINIO_ACCESS_KEY, MINIO_SECRET_KEY
    MINIO_ACCESS_KEY = username
    MINIO_SECRET_KEY = password

    # print info to log
    app.logger.info(f"Received data from user {username}:")
    app.logger.info(f"{data}")

    # Create an MQTT client 
    mqtt_client = mqtt.Client()

    # Set up the callback functions
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    # Set the username and password
    mqtt_client.username_pw_set("everyone", "everyone")

    # Connect to the local wis2box-broker
    mqtt_client.connect("172.17.0.1", 1883, 60)

    try:
        app.logger.info(f"Connecting to MinIO at {MINIO_ENDPOINT}...")
        # Connect to MinIO client
        minio_client = Minio(MINIO_ENDPOINT,
                       access_key=MINIO_ACCESS_KEY,
                       secret_key=MINIO_SECRET_KEY,
                       secure=False)

        # Convert data to bytes
        data_bytes = data.encode('utf-8')
        # Create a file-like object from the content
        data_file = io.BytesIO(data_bytes)

        # Start the MQTT network loop
        mqtt_client.loop_start()
        app.logger.info(f"Uploading data to bucket {MINIO_BUCKET_NAME}...")        
        # Upload data to MinIO
        minio_path = 'ira/iran_met_centre/data/core/weather/surface-based-observations/synop'
        minio_client.put_object(
            'wis2box-incoming',
            minio_path + '/' + filename,	
            data=data_file,
            length=len(data_bytes)
        )
        app.logger.info(f"Uploaded data to MinIO with key={minio_path}/{filename}")
        app.logger.info(f"Waiting 2 seconds for MQTT messages...")
        time.sleep(2)
        # Stop the MQTT network loop
        mqtt_client.loop_stop()
        # Disconnect from the MQTT broker
        mqtt_client.disconnect()

        result = {'status': 'success', 
                  'message': 'Uploaded data to MinIO with key=' + minio_path + '/' + filename}
    except InvalidResponseError as err:
        app.logger.error(f"MinIO.InvalidResponseError: {err}")
        result = {'status': 'error', 'message': str(err)}
    except Exception as err:
        app.logger.error(f"Exception: {err}")
        result = {'status': 'error', 'message': str(err)}

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)