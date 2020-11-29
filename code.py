"""
20201127 - 11:03:00 PM
"""
import time
import board
import busio
from analogio import AnalogIn
import adafruit_adt7410
from digitalio import DigitalInOut
from adafruit_apds9960.apds9960 import APDS9960
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import neopixel
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT


try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

local_house = secrets["local_house"]
remote_house = secrets["remote_house"]

print("\n\nR E S T A R T I N G\n\n")
print("    " + local_house.upper() + " LOCAL -->")
print("<-- " + remote_house.upper() + " REMOTE")
print(".........................\n")

print("working on:")

print("- setting up neopixels")
pixel_pin = board.A1
num_pixels = 30
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.3, auto_write=False)

# Set up color constants
RED = (255, 0, 0)
YELLOW = (255, 150, 0)
ORANGE = (255, 40, 0)
GREEN = (0, 255, 0)
TEAL = (0, 255, 120)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)
MAGENTA = (255, 0, 20)
WHITE = (255, 255, 255)
GOLD = (255, 222, 30)
PINK = (242, 90, 255)
AQUA = (50, 255, 255)
JADE = (0, 255, 40)
AMBER = (255, 100, 0)
BLACK = (0, 0, 0)
SOFTWHITE = (255, 100, 0)

# Set up neopixel helpers
def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def color_chase(color, wait):
    for i in range(num_pixels):
        pixels[i] = color
        time.sleep(wait)
        pixels.show()
    time.sleep(0.5)

def rainbow_cycle(wait):
    for j in range(255):
        for i in range(num_pixels):
            rc_index = (i * 256 // num_pixels) + j
            pixels[i] = wheel(rc_index & 255)
        pixels.show()
        time.sleep(wait)

def range_f(start, stop, step):
    x = start
    while x <= stop:
        yield x
        x -= step

def selected():
    z = 0.3
    n = 0
    while n <= 2:
        while z < 1:
            pixels.brightness = z
            pixels.show()
            z += 0.01

        while z >= 0.3:
            pixels.brightness = z
            pixels.show()
            z -= 0.01
        n += 1

    while z > 0:
        pixels.brightness = z
        pixels.show()
        z -= 0.005
    pixels.fill(BLACK)
    pixels.brightness = 0.3
    pixels.show()

def fade_in(color):
    z = 0
    pixels.fill(BLACK)
    pixels.show()
    pixels.brightness = z
    pixels.show()
    pixels.fill(color)
    pixels.show()

    while z < 1:
        pixels.brightness = z
        pixels.show()
        z += 0.005

    while z >= 0.3:
        pixels.brightness = z
        pixels.show()
        z -= 0.01

def fade_out():
    z = 0.3

    while z > 0:
        pixels.brightness = z
        pixels.show()
        time.sleep(0.05)
        z -= 0.005
    pixels.fill(BLACK)
    pixels.brightness = 0.3
    pixels.show()


# reset neopixel strip
print('- clearing the neopixel strip')
pixels.fill(GREEN)
pixels.show()
time.sleep(1)
pixels.fill(BLACK)
pixels.show()

print("- setting up wifi")
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

print('- setting up internal light sensor')
adc = AnalogIn(board.LIGHT)

print("- setting up internal temperature sensor: ADT7410")
i2c_bus = busio.I2C(board.SCL, board.SDA)
adt = adafruit_adt7410.ADT7410(i2c_bus, address=0x48)
adt.high_resolution = True

print("- setting up external gesture sensor: APDS9960")
apds = APDS9960(i2c_bus, address=0x39)
apds.enable_proximity = True
apds.enable_gesture = True

def gesture_detail(number, show_color):
    if number == 0x01:
        description = "up"
        pixels.fill(JADE)
        pixels.show()
    elif number == 0x02:
        description = "down"
        pixels.fill(MAGENTA)
        pixels.show()
    elif number == 0x03:
        description = "left"
        pixels.fill(AMBER)
        pixels.show()
    elif number == 0x04:
        description = "right"
        pixels.fill(CYAN)
        pixels.show()

    if show_color == 1:
        if number == 0x01:
            pixels.fill(JADE)
            pixels.show()
        elif number == 0x02:
            pixels.fill(MAGENTA)
            pixels.show()
        elif number == 0x03:
            pixels.fill(AMBER)
            pixels.show()
        elif number == 0x04:
            pixels.fill(CYAN)
            pixels.show()
    return description

# Define MQTT callback functions which will be called when certain events happen.
def connected(client):
    # Connected function will be called when the client is connected to Adafruit IO.
    # This is a good place to subscribe to feed changes.  The client parameter
    # passed to this function is the Adafruit IO MQTT client so you can make
    # calls against it easily.
    print("- connected to Adafruit IO! listening...")


def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("- sub'd: {0} (QOS:{1})".format(topic, granted_qos))


def unsubscribe(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a feed.
    print("- unsubscribed from {0} with PID {1}".format(topic, pid))


def disconnected(client):
    # Disconnected function will be called when the client disconnects.
    print("- disconnected from Adafruit IO!")

def on_message(client, feed_id, payload):
    # Message function will be called when a subscribed feed has a new value.
    # The feed_id parameter identifies the feed, and the payload parameter has
    # the new value.
    print("- feed {0} received new value: {1}".format(feed_id, payload))

def on_lightlevel_msg(client, topic, message):
    # Method called whenever user/feeds/battery has a new value
    print("<-- " + remote_house + " light level: {}".format(message))

def on_light_msg(client, topic, message):
    # Method called whenever user/feeds/battery has a new value
    print("<-- " + remote_house + " light: {}".format(message))

    if message == "True":
        fade_in(SOFTWHITE)
    else:
        fade_out()

def on_status_msg(client, topic, message):
    # Method called whenever user/feeds/status has a new value
    print("<-- " + remote_house + " status: {0}".format(message))

    if message == "activity":
        rainbow_cycle(0.0005)
        rainbow_cycle(0.0005)
        rainbow_cycle(0.0005)
        rainbow_cycle(0.005)
        rainbow_cycle(0.05)
    elif message == "up":
        fade_in(JADE)
    elif message == "down":
        fade_in(MAGENTA)
    elif message == "left":
        fade_in(AMBER)
    elif message == "right":
        fade_in(CYAN)
    else:
        fade_out()

    if message != "reset":
        # now that we've picked up the special status, reset it
        print("    " + local_house + " reset of " + remote_house + " status -->")
        io.publish(remote_house + "-status", "reset")

def on_temperature_msg(client, topic, message):
    # Method called whenever user/feeds/battery has a new value
    print("<-- " + remote_house + " temperature: {}F".format(message))


print("- connecting to WiFi...")
wifi.connect()
print("- connected!")

print("- setting up MQTT sockets, brokers and clients")
MQTT.set_socket(socket, esp)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=secrets["aio_username"],
    password=secrets["aio_key"],
)

# Initialize an Adafruit IO MQTT Client
io = IO_MQTT(mqtt_client)

# Connect the callback methods defined above to Adafruit IO
io.on_connect = connected
io.on_disconnect = disconnected
io.on_subscribe = subscribe
io.on_unsubscribe = unsubscribe
io.on_message = on_message

# Connect to Adafruit IO
print("- connecting to Adafruit IO...")
io.connect()

# Set up a message handlers
io.add_feed_callback(remote_house + "-lightlevel", on_lightlevel_msg)
io.add_feed_callback(remote_house + "-light", on_light_msg)
io.add_feed_callback(remote_house + "-status", on_status_msg)
io.add_feed_callback(remote_house + "-temperature", on_temperature_msg)


# Subscribe to all messages on the battery feed
io.subscribe(remote_house + "-lightlevel")
io.subscribe(remote_house + "-light")
io.subscribe(remote_house + "-status")
io.subscribe(remote_house + "-temperature")

# time variable helper
time_last_light = 0
time_last_send_light = 0
time_last_temperature = 0
time_last_check_msg = 0
time_last_sent_value = 0
time_last_gesture = 0

send_light = False

value_last_light_avg = 1
value_last_light_1 = 1
value_last_light_2 = 1
value_last_light_3 = 1
value_last_temperature = 1

print("- setup complete")
print("- starting the main loop\n\n")

print("////////////////////////////////////////////////\n")
# Start a blocking loop to check for new messages
while True:
    try:
        if (time.monotonic() - time_last_check_msg) >= 1:
            io.loop()
            time_last_check_msg = time.monotonic()

        gesture = apds.gesture()

        if gesture != 0x00:
            print("    noticed a gesture:")
            time_last_gesture = time.monotonic()
            print("    - " + gesture_detail(gesture, 1))
            gesture_old = gesture

            while (time.monotonic() - time_last_gesture) <= 5:
                gesture = apds.gesture()
                if (gesture != 0x00) and (gesture != gesture_old):
                    print("    - " + gesture_detail(gesture, 1))
                    gesture_old = gesture
                    time_last_gesture = time.monotonic()

            print("    " + local_house + "'s final gesture: " + gesture_detail(gesture_old, 0) + " -->")
            io.publish(local_house + "-status", gesture_detail(gesture_old, 0))
            selected()

        # get the light sensor value
        value_current_light = adc.value

        if abs(value_current_light - value_last_light_avg) >= 1500:

            value_to_send_light = value_current_light

            if (send_light == False) and (time_last_send_light == 0):
                send_light = True
                io.publish(local_house + "-light", str(send_light))
                time_last_send_light = time.monotonic()
                print("    light = True -->\n\n    started timer...")

            if (send_light == True) and (time_last_send_light != 0):
                time_last_send_light = time.monotonic()
                print("    light still changing. extended timer...")

            print("    significant light change: " + str(value_current_light))

        # Smooth out light values
        value_last_light_3 = value_last_light_2
        value_last_light_2 = value_last_light_1
        value_last_light_1 = value_current_light
        value_last_light_avg = (value_last_light_1 + value_last_light_2 + value_last_light_3) / 3

        if ((time.monotonic() - time_last_send_light) >= 20) and (time_last_send_light != 0):
            send_light = False
            io.publish(local_house + "-light", str(send_light))
            time_last_send_light = 0
            print("    light = false -->\n\n    it's been 20 sec. reset timer...\n")

        if (time.monotonic() - time_last_sent_value) >= 30:

            print("    " + local_house + " light: " + str(value_current_light) + " -->")
            io.publish(local_house + "-lightlevel", value_current_light)

            local_temperature_value = round(((adt.temperature * 1.8) + 32))
            print("    " + local_house + " temp : " + str(local_temperature_value) + "F -->\n")
            io.publish(local_house + "-temperature", local_temperature_value)

            time_last_sent_value = time.monotonic()

        time.sleep(0.01)
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        io.reconnect()
        continue