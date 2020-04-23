#!/usr/bin/env python

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from picamera import PiCamera
import logging
import time
import argparse
import json
import boto3
from pantilthat.pantilt import PanTilt
from threading import Semaphore

camera = PiCamera(sensor_mode=2, resolution="2592x1944")
mqttClient = None
publish = Semaphore(0)
status = {}


# Custom MQTT message callback
def picCallback(client, userdata,message):
    logger.debug("PicCallback")
    camera.start_preview()
    camera.capture('/home/pi/pipic.jpg')
    try:
        s3 = boto3.client('s3')
        with open('/home/pi/pipic.jpg',"rb") as f:
            s3.upload_fileobj(f,"iotpicbucket","pic.jpg",ExtraArgs={'ACL':'public-read'})

    except:
        logger.error("boto failed")
    camera.stop_preview()
    status['message'] = "pic done"
    status['pan'] = stand.get_pan()
    status['tilt'] = stand.get_tilt()
    publish.release();
    #try:
    #    mqttClient.publish(topic, json.dumps(picdone), 2)
    #except:
    #    logger.debug('problem with pic\n');

def ptCallback(client, userdata,message):
    logger.debug("ptCallback "+str(userdata));
    logger.debug("ptCallback "+str(message.payload));
    pload=json.loads(message.payload);
    logger.debug(pload);
    if 'tilt' in pload:
        logger.debug(pload['tilt']);
        stand.tilt(pload['tilt']);

    if 'pan' in pload:
        logger.debug(pload['pan']);
        stand.pan(pload['pan']);




stand = PanTilt();
#args = parser.parse_args()
host = "a3v1d70hhtwfc0-ats.iot.eu-west-2.amazonaws.com"
rootCAPath = "/root/certs/root-CA.crt"
certificatePath = "/root/certs/KenPi.cert.pem"
privateKeyPath = "/root/certs/KenPi.private.key"
port = 8883
clientId = "basicPubSub"
topic = "sdk/test/Python"
picTopic = "sdk/takePic"
ptTopic = "sdk/pantilt"

# Port defaults

# Configure logging
logger = logging.getLogger("AWSIoTPythonSDK.core")
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

# Init AWSIoTMQTTClient
mqttClient = AWSIoTMQTTClient(clientId)
mqttClient.configureEndpoint(host, port)
mqttClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTClient connection configuration
mqttClient.configureAutoReconnectBackoffTime(1, 32, 20)
mqttClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
mqttClient.configureDrainingFrequency(2)  # Draining: 2 Hz
mqttClient.configureConnectDisconnectTimeout(10)  # 10 sec
mqttClient.configureMQTTOperationTimeout(10)  # 5 sec

# Connect and subscribe to AWS IoT
notconnected=True
while(notconnected):
    try:
        mqttClient.connect()
        mqttClient.subscribe(picTopic, 1, picCallback)
        mqttClient.subscribe(ptTopic, 1, ptCallback)
        time.sleep(2)
        notconnected=False
    except:
        logger.debug("still connecting");
        time.sleep(1)



# Publish to the same topic in a loop forever
while True:
    publish.acquire();
    try:
        mqttClient.publish(topic,json.dumps(status) , 0)
    except:
        logger.debug('publish timeout\n');
    logger.debug('Published topic %s: %s\n' % (topic, status))

