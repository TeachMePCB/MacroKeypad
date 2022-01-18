# SPDX-FileCopyrightText: Copyright (c) 2021-2022 Jesse Robinson
#
# SPDX-License-Identifier: MIT

"""
TeachMe PCB Rev 2 Class
Description: Bring up hardware, skull keypad - Jesse Robinson
Rev: 11/8/2021
"""

import time
import busio
import board
import rotaryio
import digitalio
import neopixel
from digitalio import DigitalInOut, Direction, Pull
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
import adafruit_veml7700

i2c = busio.I2C(board.GP21, board.GP20)

# Update this to match the number of NeoPixel LEDs connected to your board.
num_pixels = 10  # was 10, 12 for encoder lights

brightnessSteps = 50
pixelBrightness = brightnessSteps / 2

pixels = neopixel.NeoPixel(board.GP19, num_pixels)
pixels.brightness = float(pixelBrightness) / brightnessSteps

spi = busio.SPI(clock=board.GP26, MOSI=board.GP27)
latch = digitalio.DigitalInOut(board.GP28)
latch.direction = digitalio.Direction.OUTPUT
latch.switch_to_output(True)
latch.value = False

RED = (255, 0, 0)
YELLOW = (255, 150, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)

pins = [
    board.GP1,
    board.GP2,
    board.GP3,
    board.GP4,
    board.GP5,
    board.GP6,
    board.GP7,
    board.GP8,
    board.GP9,
    board.GP10,
    board.GP11,
    board.GP12,
]

MEDIA = 1
KEY = 2

keymap = {
    (0): (KEY, [Keycode.ONE]),
    (1): (KEY, [Keycode.TWO]),
    (2): (KEY, [Keycode.THREE]),
    (3): (KEY, [Keycode.FOUR]),
    (4): (KEY, [Keycode.FIVE]),
    (5): (KEY, [Keycode.SIX]),
    (6): (KEY, [Keycode.SEVEN]),
    (7): (KEY, [Keycode.EIGHT]),
    (8): (KEY, [Keycode.NINE]),
    (9): (KEY, [Keycode.ZERO]),
    (10): (KEY, [Keycode.X]),  # unused
    (11): (KEY, [Keycode.Y]),  # unused
}
switches = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

for i in range(10):
    switches[i] = DigitalInOut(pins[i])
    switches[i].direction = Direction.INPUT
    switches[i].pull = Pull.UP

switches[10] = digitalio.DigitalInOut(board.GP11)
switches[11] = digitalio.DigitalInOut(board.GP12)

switch_state = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

leftEncoder = rotaryio.IncrementalEncoder(board.GP17, board.GP18)
leftEncoder_last_position = leftEncoder.position

rightEncoder = rotaryio.IncrementalEncoder(board.GP14, board.GP15)
rightEncoder_last_position = rightEncoder.position

while not spi.try_lock():
    pass

# while not i2c.try_lock():
# pass

veml7700 = adafruit_veml7700.VEML7700(i2c)

print("Ambient light:", veml7700.light)

trackColor = 0


def ledChange():
    global trackColor

    if trackColor == 0:
        pixels.fill(RED)
    elif trackColor == 1:
        pixels.fill(YELLOW)
    elif trackColor == 2:
        pixels.fill(GREEN)
    elif trackColor == 3:
        pixels.fill(CYAN)
    elif trackColor == 4:
        pixels.fill(BLUE)
    elif trackColor == 5:
        pixels.fill(PURPLE)
    else:
        trackColor = 0
        pixels.fill(RED)


spi.configure(baudrate=5000000, phase=0, polarity=0)
spi.write(bytes([0x00]))
latch.value = True
latch.value = False
time.sleep(1)


def eye_update(left_eye, right_eye):
    """

    :param left_eye:
    :param right_eye:
    :param eye_write_byte:
    :return:
    """
    left_eye_red = not left_eye[0]
    left_eye_green = not left_eye[1]
    left_eye_blue = not left_eye[2]

    right_eye_red = not right_eye[0]
    right_eye_green = not right_eye[1]
    right_eye_blue = not right_eye[2]

    eye_write_byte = (
            (left_eye_red << 0)
            | (left_eye_green << 1)
            | (left_eye_blue << 2)
            | (right_eye_red << 3)
            | (right_eye_green << 4)
            | (right_eye_blue << 5)
    )
    spi.write(bytes([eye_write_byte]))
    latch.value = False
    latch.value = True
    return eye_write_byte
    # print("EyeWrite: ", eyeWriteByte)


ledChange()
# order RGB
eye_update(left_eye=[1, 0, 0], right_eye=[0, 1, 1])

useUSB = False

# if you want to use without USB (for lights and such) your HID calls will hang, pressing right encoder upon bootup disables USB calls to prevent this
if not switches[10].value:
    useUSB = True

if useUSB == True:
    kbd = Keyboard(usb_hid.devices)
    cc = ConsumerControl(usb_hid.devices)

while True:

    ambientLight = veml7700.light
    # print("Ambient light:", ambientLight)

    for button in range(10):
        if switch_state[button] == 0:
            if not switches[button].value:
                try:
                    if keymap[button][0] == KEY:
                        if useUSB == True:
                            kbd.press(*keymap[button][1])
                    else:
                        if useUSB == True:
                            cc.send(keymap[button][1])
                except ValueError:  # deals w six key limit
                    pass
                switch_state[button] = 1

        if switch_state[button] == 1:
            if switches[button].value:
                try:
                    if keymap[button][0] == KEY:
                        if useUSB == True:
                            kbd.release(*keymap[button][1])
                except ValueError:
                    pass
                switch_state[button] = 0

    button = 10
    if switch_state[button] == 0:
        if switches[button].value:
            try:
                if keymap[button][0] == KEY:
                    pass
                    trackColor = trackColor + 1
                    ledChange()
                    # kbd.press(*keymap[button][1])
                else:
                    pass
                    # cc.send(keymap[button][1])
            except ValueError:  # deals w six key limit
                pass
            switch_state[button] = 1

    if switch_state[button] == 1:
        if not switches[button].value:
            try:
                if keymap[button][0] == KEY:
                    pass
                    # kbd.release(*keymap[button][1])
            except ValueError:
                pass
            switch_state[button] = 0

    button = 11
    if switch_state[button] == 0:
        if switches[button].value:
            try:
                if keymap[button][0] == KEY:
                    pass
                    if useUSB == True:
                        cc.send(ConsumerControlCode.PLAY_PAUSE)
                    # kbd.press(*keymap[button][1])
                else:
                    pass
                    # cc.send(keymap[button][1])
            except ValueError:  # deals w six key limit
                pass
            switch_state[button] = 1

    if switch_state[button] == 1:
        if not switches[button].value:
            try:
                if keymap[button][0] == KEY:
                    pass
                    # kbd.release(*keymap[button][1])
            except ValueError:
                pass
            switch_state[button] = 0

    current_position = leftEncoder.position
    position_change = current_position - leftEncoder_last_position
    if position_change > 0:
        for _ in range(position_change):
            if pixelBrightness < brightnessSteps:
                pixelBrightness = pixelBrightness + 1
        # print(pixelBrightness)
        pixels.brightness = float(pixelBrightness) / brightnessSteps
    elif position_change < 0:
        for _ in range(-position_change):
            if pixelBrightness > 0:
                pixelBrightness = pixelBrightness - 1
        # print(pixelBrightness)
        pixels.brightness = float(pixelBrightness) / brightnessSteps
    leftEncoder_last_position = current_position

    current_position = rightEncoder.position
    position_change = current_position - rightEncoder_last_position
    if position_change > 0:
        for _ in range(position_change):
            if useUSB == True:
                cc.send(ConsumerControlCode.VOLUME_INCREMENT)
        # print(current_position)
    elif position_change < 0:
        for _ in range(-position_change):
            if useUSB == True:
                cc.send(ConsumerControlCode.VOLUME_DECREMENT)
        # print(current_position)
    rightEncoder_last_position = current_position

    time.sleep(0.010)  # debounce
