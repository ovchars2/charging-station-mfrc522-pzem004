import asyncio
import time
import spidev
import RPi.GPIO as GPIO
from rpi_ws281x import Color
from RPLCD.i2c import CharLCD as i2c_lcd
from RPLCD.gpio import CharLCD as lcd
import board
import busio
from string_utils import is_full_string
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
import serial
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu

class Relay:
    """
    A simple class for a Relay. Takes the pin number and default state of the pin as an argument.
    Performs on and off actions and tracks it's state.
    """

    def __init__(self, pin: int, relay_state: int):
        self._pin = pin
        self._relay_state = relay_state
        self._inverse_logic = False
        GPIO.setup(self._pin, GPIO.OUT)
        if relay_state == GPIO.HIGH:
            self._inverse_logic = True
        GPIO.output(self._pin, relay_state)

    def on(self):
        """
        Turn the relay on.
        :return:
        """
        if self._relay_state == GPIO.LOW:
            GPIO.output(self._pin, GPIO.HIGH)
            self._relay_state = GPIO.HIGH
        elif self._inverse_logic:
            self.off()

    def off(self):
        """
        Turn the relay off.
        :return:
        """
        if self._relay_state == GPIO.HIGH:
            GPIO.output(self._pin, GPIO.LOW)
            self._relay_state = GPIO.LOW
        elif self._inverse_logic:
            self.on()

    def toggle(self):
        """
        Toggle the relay state.
        :return:
        """
        if self._relay_state == GPIO.HIGH:
            GPIO.output(self._pin, GPIO.LOW)
            self._relay_state = GPIO.LOW
        else:
            GPIO.output(self._pin, GPIO.HIGH)
            self._relay_state = GPIO.HIGH


class LEDStrip:
    """
    Class with LED strip color values.
    """

    RED: Color = Color(255, 0, 0)
    GREEN: Color = Color(0, 255, 0)
    BLUE: Color = Color(0, 0, 255)
    YELLOW: Color = Color(245, 241, 29)
    ORANGE: Color = Color(255, 144, 59)
    WHITE: Color = Color(255, 255, 255)
    OFF: Color = Color(0, 0, 0)


class PowerMeter:
    def __init__(self, port: str):
        self.open_port = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=8,
            parity='N',
            stopbits=1,
            xonxoff=0
        )
        print(f'Initialized PZEM-004T on {port}')
        self.modbus_master = modbus_rtu.RtuMaster(self.open_port)
        self.modbus_master.set_timeout(2.0)
        self.modbus_master.set_verbose(True)

    def __read_pzem_data(self):
        try:
            data = self.modbus_master.execute(1, cst.READ_INPUT_REGISTERS, 0, 10)

            ret = dict()

            ret['voltage'] = data[0] / 10.0  # [V]
            ret['current'] = (data[1] + (data[2] << 16)) / 1000.0  # [A]
            ret['power'] = (data[3] + (data[4] << 16)) / 10.0  # [W]
            ret['energy'] = data[5] + (data[6] << 16)  # [Wh]
            ret['frequency'] = data[7] / 10.0  # [Hz]
            ret['powerFactor'] = data[8] / 100.0
            ret['alarm'] = data[9]  # 0 = no alarm

            return ret
        except Exception as e:
            return None

    def reset(self):
        # todo
        pass

    def get_current_power_draw(self):
        data = self.__read_pzem_data()
        if data is None:
            return 0
        else:
            return data['power']

    def get_energy_consumption(self):
        data = self.__read_pzem_data()
        if data is None:
            return 0
        else:
            return data['energy']


class LCDModule:
    """
    A class for LCD module with I2C support.
    Displays the current consumption/power of the power meter, connector availability and other important messages.
    """

    def __init__(self, lcd_info: dict):
        self._lcd = None
        self.is_lcd_supported: bool = lcd_info["is_supported"]
        self._i2c_address: str = lcd_info["i2c_address"]

        self.row1_text = ' '
        self.row2_text = ' '
        self.row3_text = ' '
        self.row4_text = ' '

        print('LCD initialization - supported:', self.is_lcd_supported, 'address:', self._i2c_address)
        try:
            if self.is_lcd_supported:
                if is_full_string(self._i2c_address):
                    self._lcd = i2c_lcd(i2c_expander="PCF8574",
                                        address=int(self._i2c_address, 16),
                                        cols=20,
                                        rows=4,
                                        charmap='ST0B')
                else:
                    self._lcd = lcd(pin_rs=15,
                                    pin_rw=18,
                                    pin_e=16,
                                    pins_data=[21, 22, 23, 24],
                                    rows=4,
                                    cols=20)
                self.clear()
        except Exception as ex:
            self.is_lcd_supported = False
            print(ex)

    def clear(self):
        if self._lcd is None:
            return
        self._lcd.clear()

    async def __display_in_rows(self, delay: int, row1_msg: str = None, row2_msg: str = None, row3_msg: str = None,
                                row4_msg: str = None):
        if self._lcd is None or not self.is_lcd_supported:
            return

        if row1_msg is not None:
            self.row1_text = row1_msg
        if row2_msg is not None:
            self.row2_text = row2_msg
        if row3_msg is not None:
            self.row3_text = row3_msg
        if row4_msg is not None:
            self.row4_text = row4_msg

        self.clear()

        self._lcd.cursor_pos = (0, 0)
        self._lcd.write_string(self.row1_text)
        self._lcd.cursor_pos = (1, 0)
        self._lcd.write_string(self.row2_text)
        self._lcd.cursor_pos = (2, 0)
        self._lcd.write_string(self.row3_text)
        self._lcd.cursor_pos = (3, 0)
        self._lcd.write_string(self.row4_text)

        await asyncio.sleep(delay)

    async def display_current_status(self, connector_id: int, is_charging: bool, power: float):
        """
        Display the connector's current status to the LCD.
        :param connector_id: A connector ID
        :param is_charging: Connector's charging state
        :param consumption: Current value of the meter
        :return:
        """
        row2_msg: str = "Available"
        if is_charging:
            if power > 1000:
                appendix = "kW"
            else:
                appendix = "W"
            row2_msg = f"Power: {power} {appendix}"
        await self.__display_in_rows(row1_msg=f"Connector: {connector_id}",
                                     row2_msg=row2_msg,
                                     delay=3)

    async def display_card_detected(self):
        await self.__display_in_rows(row4_msg="Card read", row3_msg=" ", delay=3)
        await self.__display_in_rows(row4_msg=" ", row3_msg=" ", delay=0)

    async def display_invalid_card(self):
        await self.__display_in_rows(row3_msg="Card", row4_msg="Unauthorized", delay=3)
        await self.__display_in_rows(row3_msg=" ", row4_msg=" ", delay=1)

    async def start_charging_message(self, connector_id: int):
        await self.__display_in_rows(row1_msg="Started charging",
                                     row2_msg=f"on {connector_id}",
                                     delay=4)

    async def stop_charging_message(self, connector_id: int):
        await self.__display_in_rows(row1_msg="Stopped charging",
                                     row2_msg=f"on {connector_id}",
                                     delay=4)

    async def connector_unavailable(self, connector_id: int):
        if connector_id == -1:
            await self.__display_in_rows(row3_msg="No available",
                                         row4_msg="connectors",
                                         delay=4)
            await self.__display_in_rows(row3_msg=" ",
                                         row4_msg=" ",
                                         delay=0)
        else:
            await self.__display_in_rows(row3_msg=f"Connector {connector_id}",
                                         row4_msg="unavailable",
                                         delay=4)
            await self.__display_in_rows(row3_msg=" ",
                                         row4_msg=" ",
                                         delay=0)

    async def display_error(self, connector_id: int, msg: str):
        if connector_id == -1:
            await self.__display_in_rows(row4_msg="Error",
                                         row3_msg=" ",
                                         delay=3)
        else:
            await self.__display_in_rows(row1_msg="Fault on",
                                         row2_msg=f"Connector {connector_id}:",
                                         row3_msg='Message:',
                                         row4_msg=msg,
                                         delay=3)

    async def not_connected_error(self):
        await self.__display_in_rows(row1_msg="Charging",
                                     row2_msg="unavailable",
                                     delay=4)


class PN532Reader:
    def __init__(self, hard_reset_pin):
        GPIO.setup(hard_reset_pin, GPIO.OUT)
        self._hard_reset_pin = hard_reset_pin
        self.reset()
        self._i2c = busio.I2C(board.SCL, board.SDA)
        self._reset_pin = DigitalInOut(board.D6)
        self._req_pin = DigitalInOut(board.D12)
        self._reader: PN532_I2C = PN532_I2C(self._i2c, debug=False, reset=self._reset_pin, req=self._req_pin)
        self._reader.SAM_configuration()

    def read_passive(self):
        return self._reader.read_passive_target(timeout=.3)

    def reset(self):
        print("Reset PN532")
        GPIO.output(self._hard_reset_pin, GPIO.LOW)
        time.sleep(.2)
        GPIO.output(self._hard_reset_pin, GPIO.HIGH)
        time.sleep(.2)
