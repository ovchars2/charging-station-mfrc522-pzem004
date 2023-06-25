import minimalmodbus
import time


class PZEM004T_v3:
    REG_VOLTAGE = 0x0000
    REG_CURRENT_L = 0x0001
    REG_CURRENT_H = 0X0002
    REG_POWER_L = 0x0003
    REG_POWER_H = 0x0004
    REG_ENERGY_L = 0x0005
    REG_ENERGY_H = 0x0006
    REG_FREQUENCY = 0x0007
    REG_PF = 0x0008
    REG_ALARM = 0x0009

    CMD_RHR = 0x03
    CMD_RIR = 0X04
    CMD_WSR = 0x06
    CMD_CAL = 0x41
    CMD_REST = 0x42

    WREG_ALARM_THR = 0x0001
    WREG_ADDR = 0x0002

    UPDATE_TIME = 200

    RESPONSE_SIZE = 32
    READ_TIMEOUT = 100

    INVALID_ADDRESS = 0x00

    PZEM_DEFAULT_ADDR = 0xF8
    PZEM_BAUD_RATE = 9600

    READ_VALUES_MIN_ADDR = 0x00
    VALUE_REGISTERS_SIZE = 0x0A

    INVALID_ALARMS_VALUE = -1

    _CRC_TABLE = [
        0X0000, 0XC0C1, 0XC181, 0X0140, 0XC301, 0X03C0, 0X0280, 0XC241,
        0XC601, 0X06C0, 0X0780, 0XC741, 0X0500, 0XC5C1, 0XC481, 0X0440,
        0XCC01, 0X0CC0, 0X0D80, 0XCD41, 0X0F00, 0XCFC1, 0XCE81, 0X0E40,
        0X0A00, 0XCAC1, 0XCB81, 0X0B40, 0XC901, 0X09C0, 0X0880, 0XC841,
        0XD801, 0X18C0, 0X1980, 0XD941, 0X1B00, 0XDBC1, 0XDA81, 0X1A40,
        0X1E00, 0XDEC1, 0XDF81, 0X1F40, 0XDD01, 0X1DC0, 0X1C80, 0XDC41,
        0X1400, 0XD4C1, 0XD581, 0X1540, 0XD701, 0X17C0, 0X1680, 0XD641,
        0XD201, 0X12C0, 0X1380, 0XD341, 0X1100, 0XD1C1, 0XD081, 0X1040,
        0XF001, 0X30C0, 0X3180, 0XF141, 0X3300, 0XF3C1, 0XF281, 0X3240,
        0X3600, 0XF6C1, 0XF781, 0X3740, 0XF501, 0X35C0, 0X3480, 0XF441,
        0X3C00, 0XFCC1, 0XFD81, 0X3D40, 0XFF01, 0X3FC0, 0X3E80, 0XFE41,
        0XFA01, 0X3AC0, 0X3B80, 0XFB41, 0X3900, 0XF9C1, 0XF881, 0X3840,
        0X2800, 0XE8C1, 0XE981, 0X2940, 0XEB01, 0X2BC0, 0X2A80, 0XEA41,
        0XEE01, 0X2EC0, 0X2F80, 0XEF41, 0X2D00, 0XEDC1, 0XEC81, 0X2C40,
        0XE401, 0X24C0, 0X2580, 0XE541, 0X2700, 0XE7C1, 0XE681, 0X2640,
        0X2200, 0XE2C1, 0XE381, 0X2340, 0XE101, 0X21C0, 0X2080, 0XE041,
        0XA001, 0X60C0, 0X6180, 0XA141, 0X6300, 0XA3C1, 0XA281, 0X6240,
        0X6600, 0XA6C1, 0XA781, 0X6740, 0XA501, 0X65C0, 0X6480, 0XA441,
        0X6C00, 0XACC1, 0XAD81, 0X6D40, 0XAF01, 0X6FC0, 0X6E80, 0XAE41,
        0XAA01, 0X6AC0, 0X6B80, 0XAB41, 0X6900, 0XA9C1, 0XA881, 0X6840,
        0X7800, 0XB8C1, 0XB981, 0X7940, 0XBB01, 0X7BC0, 0X7A80, 0XBA41,
        0XBE01, 0X7EC0, 0X7F80, 0XBF41, 0X7D00, 0XBDC1, 0XBC81, 0X7C40,
        0XB401, 0X74C0, 0X7580, 0XB541, 0X7700, 0XB7C1, 0XB681, 0X7640,
        0X7200, 0XB2C1, 0XB381, 0X7340, 0XB101, 0X71C0, 0X7080, 0XB041,
        0X5000, 0X90C1, 0X9181, 0X5140, 0X9301, 0X53C0, 0X5280, 0X9241,
        0X9601, 0X56C0, 0X5780, 0X9741, 0X5500, 0X95C1, 0X9481, 0X5440,
        0X9C01, 0X5CC0, 0X5D80, 0X9D41, 0X5F00, 0X9FC1, 0X9E81, 0X5E40,
        0X5A00, 0X9AC1, 0X9B81, 0X5B40, 0X9901, 0X59C0, 0X5880, 0X9841,
        0X8801, 0X48C0, 0X4980, 0X8941, 0X4B00, 0X8BC1, 0X8A81, 0X4A40,
        0X4E00, 0X8EC1, 0X8F81, 0X4F40, 0X8D01, 0X4DC0, 0X4C80, 0X8C41,
        0X4400, 0X84C1, 0X8581, 0X4540, 0X8701, 0X47C0, 0X4680, 0X8641,
        0X8201, 0X42C0, 0X4380, 0X8341, 0X4100, 0X81C1, 0X8081, 0X4040
    ]

    def __init__(self, port: str, addr=PZEM_DEFAULT_ADDR, timeout=2.0) -> None:
        self._addr = addr

        self.modbus_master = minimalmodbus.Instrument(port, addr)
        self.modbus_master.serial.timeout = timeout

        self._voltage = float('nan')
        self._current = float('nan')
        self._power = float('nan')
        self._energy = float('nan')
        self._frequency = float('nan')
        self._pf = float('nan')
        self._alarm = self.INVALID_ALARMS_VALUE

    def close(self) -> None:
        self.modbus_master.serial.close()

    # * Get line voltage in Volts
    # *
    # * @return current L-N volage
    def get_voltage(self) -> float:
        if not self.update_values():
            return float('nan')
        return self._voltage

    # * Get line in Amps
    # *
    # * @return line current
    def get_current(self) -> float:
        if not self.update_values():
            return float('nan')
        return self._current

    # * Get Active power in W
    # *
    # * @return active power in W
    def get_power(self) -> float:
        if not self.update_values():
            return float('nan')
        return self._power

    # * Get Active energy in Wh since last reset
    # *
    # * @return active energy in Wh
    def get_energy(self) -> float:
        if not self.update_values():
            return float('nan')
        return self._energy

    # * Reset the Energy counter on the device
    # *
    # * @return success
    def reset_energy(self) -> bool:  # TODO test execution
        try:
            self.modbus_master.serial.write(bytearray([self._addr, self.CMD_REST]))
            data = self.modbus_master.serial.read(5)
            print('Energy reset done.')
            print(data)
            print('Energy reset done.')
            return True
        except Exception as e:
            print(e)
            print('Energy reset failed.')
            return False

    # * Get current line frequency in Hz
    # *
    # * @return line frequency in Hz
    def get_frequency(self) -> float:
        if not self.update_values():
            return float('nan')
        return self._frequency

    # * Get power factor of load
    # *
    # * @return load power factor
    def get_pf(self) -> float:
        if not self.update_values():
            return float('nan')
        return self._pf

    def update_values(self) -> bool:
        try:
            reg_str = self.modbus_master.read_string(registeraddress=self.READ_VALUES_MIN_ADDR,
                                                     number_of_registers=self.VALUE_REGISTERS_SIZE,
                                                     functioncode=self.CMD_RIR)

            data = bytearray()
            data.extend(reg_str)

            self._voltage = data[0] / 10.0  # [V]
            self._current = (data[1] + (data[2] << 16)) / 1000.0  # [A]
            self._power = (data[3] + (data[4] << 16)) / 10.0  # [W]
            self._energy = data[5] + (data[6] << 16)  # [Wh]
            self._frequency = data[7] / 10.0  # [Hz]
            self._pf = data[8] / 100.0  # [pf] - no unit
            self._alarm = data[9]  # 0 = no alarm

            print(data)
            print(self._energy)
            return True
        except Exception as e:
            print(e)
            return False


if __name__ == '__main__':
    pm = PZEM004T_v3('/dev/ttyS0')

    while True:
        print(pm.get_voltage())
        print(pm.get_current())
        print(pm.get_power())
        print(pm.get_energy())
        print(pm.get_frequency())
        print("--------------------")

        time.sleep(1)
        pm.reset_energy()
        time.sleep(2)
