import serial
import math
from channel import Channel


ENCODING = "utf-8"
CHANNEL_COUNT = 8


class NoConnectionException(Exception):
    pass


class MockSerial:
    pendingSet = False
    response = None

    def write(self, val):
        if (val.startswith(b"!")):
            self.pendingSet = True
        else:
            self.response = val[0:4] + b"1" + b"+"

    def read_until(self, _):
        if (self.pendingSet):
            self.pendingSet = False
            return b"OK"
        elif (self.response):
            resp = self.response
            self.response = None
            return resp
        else:
            print("Error 1")
            return b"ERROR"

    def close(self):
        pass


class Interface:
    ser = None
    channels = []

    def connect(self, port):
        if port.startswith("sim"):
            self.ser = MockSerial()
        else:
            self.ser = serial.Serial(port, timeout=0.1, write_timeout=0.1)

    def getAmpState(self):
        channels = []
        print("Getting amp state")
        for i in range(CHANNEL_COUNT):
            c = Channel()
            c.id = i
            c.powerOn = self.queryPowerState(i)
            c.volume = self.queryVolume(i)
            c.source = self.querySource(i)
            c.mute = self.queryMute(i)
            c.treble = self.queryTreble(i)
            c.bass = self.queryBass(i)
            c.balance = self.queryBalance(i)
            channels.append(c)
        print("Done etting amp state")
        return channels

    def checkIfAmpChanged(self):
        changedChannels = []
        channels = self.getAmpState()
        for i in range(CHANNEL_COUNT):
            if i >= len(self.channels) or channels[i] != self.channels[i]:
                changedChannels.append(channels[i])
        self.channels = channels
        return changedChannels

    def disconnect(self):
        self.ser.close()

    def togglePower(self, channel):
        self.sendPowerCommand(channel, not self.channels[channel].powerOn)

    def toggleMute(self, channel):
        self.sendMuteCommand(channel, not self.channels[channel].mute)

    def sendPowerCommand(self, channel, setToOn):
        if self.sendCommand(channel, "PR", 1 if setToOn else 0):
            self.channels[channel].powerOn = setToOn

    def sendMuteCommand(self, channel, setToOn):
        if self.sendCommand(channel, "MU", 1 if setToOn else 0):
            self.channels[channel].mute = setToOn

    def selectSource(self, channel, source):
        if self.sendCommand(channel, "SS", source + 1):
            self.channels[channel].source = source

    def setVolume(self, channel, volume):
        scaledVol = math.ceil(int(volume) * 0.38)
        if self.sendCommand(channel, "VO", scaledVol):
            self.channels[channel].volume = volume

    def setTreble(self, channel, treble):
        scaledTreble = math.ceil(int(treble) * 0.14)
        if self.sendCommand(channel, "TR", scaledTreble):
            self.channels[channel].treble = treble

    def setBass(self, channel, bass):
        scaledBass = math.ceil(int(bass) * 0.14)
        if self.sendCommand(channel, "BS", scaledBass):
            self.channels[channel].bass = bass

    def setBalance(self, channel, balance):
        scaledBalance = math.ceil(int(balance) * 0.63)
        if self.sendCommand(channel, "BA", scaledBalance):
            self.channels[channel].balance = balance

    def queryPowerState(self, channel):
        return self.getBoolFromResponse(self.sendQuery(channel, "PR"))

    def queryVolume(self, channel):
        resp = self.getNumberFromResponse(self.sendQuery(channel, "VO"))
        return int(resp / 0.38)

    def querySource(self, channel):
        resp = self.getNumberFromResponse(self.sendQuery(channel, "SS"))
        return resp - 1

    def queryMute(self, channel):
        return self.getBoolFromResponse(self.sendQuery(channel, "MU"))

    def queryTreble(self, channel):
        resp = self.getNumberFromResponse(self.sendQuery(channel, "TR"))
        return int(resp / 0.14)

    def queryBass(self, channel):
        resp = self.getNumberFromResponse(self.sendQuery(channel, "BS"))
        return int(resp / 0.14)

    def queryBalance(self, channel):
        resp = self.getNumberFromResponse(self.sendQuery(channel, "BA"))
        return int(resp / 0.63)

    def getNumberFromResponse(self, response):
        if response is None:
            return -1

        number = response[4: 6]
        if (number.endswith("+")):
            number = number[: -1]
        return int(number)

    def getBoolFromResponse(self, response):
        if response is None:
            return False
        return response[4] == "1"

    def sendCommand(self, channel, attribute, value):
        # self.ser.reset_input_buffer()
        # self.ser.reset_output_buffer()
        command = '!{}{}{}+'.format(channel + 1, attribute, value)
        self.ser.write(command.encode(ENCODING))
        resp = self.ser.read_until(b"K").strip(b"\r")
        print("Command response {}".format(resp))
        if len(resp) < 2:
            print("Send command raised exception")
            raise NoConnectionException
        return resp.decode(ENCODING) == "OK"

    def sendQuery(self, channel, attribute):
        # self.ser.reset_input_buffer()
        # self.ser.reset_output_buffer()
        query = '?{}{}+'.format(channel + 1, attribute)
        self.ser.write(query.encode(ENCODING))
        resp = self.ser.read_until(b"+").strip(b"\r")
        print("Query response {}".format(resp))
        if len(resp) < 5:
            print("Query raises exception")
            raise NoConnectionException
        return resp.decode(ENCODING)
