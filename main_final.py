import numpy as np
from csv import writer
import pickle
import time
import smtplib, ssl
import urllib.request
import json
import Adafruit_DHT

import RPi.GPIO as GPIO

servoPIN = 17
mosi = 21

GPIO.setmode(GPIO.BCM)
GPIO.setup(servoPIN, GPIO.OUT)
GPIO.setup(mosi, GPIO.IN)

pwm = GPIO.PWM(servoPIN, 50)
pwm.start(0)


def SetAngle(angle):
    duty = angle / 18 + 2
    GPIO.output(servoPIN, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(1)
    GPIO.output(servoPIN, False)
    pwm.ChangeDutyCycle(0)


API = "fN0ouiz3LVTVcnoRk9ReTpCOTgArnQU6"
countryCode = "IN"
city = "Tiruchirappalli"


def location(countrycode, city):
    url = "http://dataservice.accuweather.com/locations/v1/cities/" + countrycode + "/search?apikey=" + API + "&q=" + city + "&details=true"
    # print(url)
    with urllib.request.urlopen(url) as url:
        data = json.loads(url.read().decode())
    loation_val = data[0]['Key']
    # print(loation_val)
    return loation_val


def rows_no():
    with open('austin_final.csv', 'r') as f_object:
        rows = sum(1 for line in f_object)
        return rows


while True:
    key = location(countryCode, city)
    url = "http://dataservice.accuweather.com/currentconditions/v1/" + key + "?apikey=" + API + "&details=true"
    # print(url)
    with urllib.request.urlopen(url) as url:
        data = json.loads(url.read().decode())
        # print(data)

    # temp =  data[0]['Temperature']['Metric']['Value']
    # humid = data[0]['RelativeHumidity']

    dew_point = data[0]['DewPoint']['Metric']['Value']
    pressure = data[0]['Pressure']['Imperial']['Value']
    visibility = data[0]['Visibility']['Imperial']['Value']
    wind_speed = data[0]['Wind']['Speed']['Imperial']['Value']
    wind_gust = data[0]['WindGust']['Speed']['Imperial']['Value']
    precipation_sum = data[0]['PrecipitationSummary']['Precipitation']['Imperial']['Value']
    # print(temp,humid)

    # Sensor value
    humid, temp = Adafruit_DHT.read_retry(11, 4)
    print('Temp: {0:0.1f} C  Humidity: {1:0.1f} %'.format(temp, humid))

    # give a sample input to test our model
    # this is a 2-D vector that contains values
    # for each column in the dataset.
    # temp = 33  # value from temperature and humidity sensor
    # humid = 50  # value from temperature and humiidity sensor
    inp = np.array([[temp], [temp], [temp], [dew_point], [dew_point], [dew_point], [humid], [humid],
                    [humid], [pressure], [visibility], [visibility], [visibility], [wind_speed], [wind_speed],
                    [wind_gust], [precipation_sum]])
    list_app = [rows_no() - 1, temp, temp, temp, dew_point, dew_point, dew_point, humid, humid, humid, pressure,
                visibility,
                visibility, visibility, wind_speed, wind_speed, wind_gust, precipation_sum]
    with open('austin_final.csv', 'a') as f_object:

        # Pass this file object to csv.writer()
        # and get a writer object
        writer_object = writer(f_object)

        # Pass the list as an argument into
        # the writerow()
        writer_object.writerow(list_app)

        # Close the file object
        f_object.close()
    inp = inp.reshape(1, -1)
    filename = 'finalized_model.sav'
    clf = pickle.load(open(filename, 'rb'))
    # print the output.
    print("The Temperature is %.3f C and the Humidity is %.3f PPM" % (temp, humid))
    rainfall_predicted = clf.predict(inp)[0][0]
    if rainfall_predicted < 0:
        rainfall_predicted = 0
    print('The Expected rainfall is: %.3f inches' % rainfall_predicted)
    # analog_soil_moisture = 450  # value from soil moisture sensor

    if GPIO.input(mosi):
        analog_soil_moisture = 1000
    else:
        panalog_soil_moisture = 0

    analog_soil_moisture = analog_soil_moisture / 1023
    moisture_perc = 100 - (analog_soil_moisture * 100)
    soil_water_inches = (moisture_perc * 12) / 100
    print("The soil contains water %.3f inches" % soil_water_inches)

    # to produce 4000kg/hectare of rice
    water_required_lit = 10000000
    water_required_inc = (water_required_lit * 61.02) / 100000000
    water_required_gallons = water_required_lit * 0.264172
    print("The amount of water required is %.3f inches" % water_required_inc)
    if (rainfall_predicted + soil_water_inches) > water_required_inc:
        print("Flooding of fields. Please Create proper water flow.")
        fromaddr = "sender@gmail.com"
        toaddr = "receiver@gmail.com"
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        password = input("Type your password and press enter: ")
        server.login(fromaddr, password)

        text = "The Temperature is %.3f C and the Humidity is %.3f PPM.\n" % (
            temp,
            humid) + "The Expected rainfall is %.3f inches.\n" % rainfall_predicted + "The soil contains water %.3f inches.\n" % soil_water_inches
        subject = "Flooding Alert!!!"
        message = 'Subject: {}\n\n{}'.format(subject, text)
        server.sendmail(fromaddr, toaddr, message)
        server.quit()
        print("Successfully, Mail Sent")
        print(text)
        break
        # print(text)
        # time.sleep(3600)
    else:

        inches_of_water_from_motor = water_required_inc - (rainfall_predicted + soil_water_inches)
        print("The amount of water to be supplied by motor is %.3f inches" % inches_of_water_from_motor)
        fromaddr = "sender@gmail.com"
        toaddr = "receeiver@gmail.com"
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        password = input("Type your password and press enter: ")
        server.login(fromaddr, password)

        text = "The Temperature is %.3f C and the Humidity is %.3f PPM.\n" % (
            temp,
            humid) + "The Expected rainfall is %.3f inches.\n" % rainfall_predicted + "The soil contains water %.3f inches.\n" % soil_water_inches + "The amount of water to be supplied by motor is %.3f inches." % inches_of_water_from_motor

        subject = "Regular Irrigation Update"
        message = 'Subject: {}\n\n{}'.format(subject, text)
        server.sendmail(fromaddr, toaddr, message)
        server.quit()
        print("Successfully, Mail Sent")
        print(text)
        vol_pvc = 18000
        time_def_min = int(water_required_gallons/vol_pvc) % 60
        time_def_sec = time_def_min*60
        SetAngle(90)
        time.sleep(time_def_sec)
        SetAngle(0)
        time.sleep(3600-time_def_sec)

pwm.stop()
GPIO.cleanup()
