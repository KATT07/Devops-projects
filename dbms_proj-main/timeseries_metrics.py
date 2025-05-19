"""
This will save timeseries data to influxdb
ideally run this script every min
"""

import mysql.connector
import paho.mqtt.client as mqtt

mydb = mysql.connector.connect(
    host="localhost",
    user="xxx",
    password="xxx",
    database='xxx'
)

mycursor = mydb.cursor()

q = "select count(*) from users;"
mycursor.execute(q)
r1 = mycursor.fetchall()
q = "select count(*) from messages;"
mycursor.execute(q)
r2 = mycursor.fetchall()
print(r1, r2)

# Edit These to match your config
broker_address = "xxx"
username = 'xxx'
password = 'xxx'
client_name = 'script'
port = 1883
topic = "dbms/no_users"
topic2 = "dbms/no_messages"

client = mqtt.Client()
client.username_pw_set(username, password)
client.connect(broker_address)  # connect to broker

client.publish(topic, int(r1[0][0]))  # publish
client.publish(topic2, int(r2[0][0]))  # publish
