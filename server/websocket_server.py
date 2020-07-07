#!/usr/bin/env python

import asyncio
import websockets
import json
import time
import sys
from mrc88_interface import Interface, NoConnectionException
from channel import Channel


class WebSocketServer:

    def __init__(self, amp):
        self.nextStateUpdate = time.time()
        self.connections = set()
        try:
            self.amp.checkIfAmpChanged()
            self.ampConnected = True
        except NoConnectionException:
            self.ampConnected = False

    def start(self):
        start_server = websockets.serve(self.handleWebSocket, "0.0.0.0", 8765)
        print("Awaiting websocket connections")
        asyncio.get_event_loop().run_until_complete(start_server)
        self.pollTask = asyncio.get_event_loop().create_task(self.checkAmpPeriodically())
        asyncio.get_event_loop().run_forever()
        try:
            self.pollTask.cancel()
        except asyncio.CancelledError:
            print("Stopped polling amp")

    async def registerClient(self, websocket):
        self.connections.add(websocket)

    async def removeClient(self, websocket):
        self.connections.remove(websocket)

    async def handleWebSocket(self, websocket, path):
        await self.registerClient(websocket)
        try:
            async for message in websocket:
                jsn = json.loads(message)
                operation = jsn["operation"]
                if operation == "command":
                    await self.handleCommand(websocket, jsn)
                elif operation == "getState":
                    await self.updateState(websocket, jsn["id"])
        except websockets.exceptions.ConnectionClosedError:
            print("Connection closed for one client")
        finally:
            await self.removeClient(websocket)

    async def handleCommand(self, websocket, jsn):
        try:
            t = jsn['type']
            channel = jsn['id']
            value = jsn['value']
            if t == 'volume':
                self.amp.setVolume(channel, value)
            elif t == 'input':
                self.amp.selectSource(channel, value)
            elif t == 'power':
                self.amp.togglePower(channel)
            elif t == 'treble':
                self.amp.setTreble(channel, value)
            elif t == 'bass':
                self.amp.setBass(channel, value)
            elif t == 'balance':
                self.amp.setBalance(channel, value)

            for ws in self.connections:
                if ws is not websocket:
                    await self.updateState(ws, channel)
        except NoConnectionException:
            await self.sendNoAmp()

    def getCurrentState(self, channel):
        data = []
        if channel == -1:
            for channel in self.amp.channels:
                data.append(channel)
        else:
            data.append(self.amp.channels[channel])
        return data

    async def updateState(self, websocket, channel):
        if self.ampConnected:
            await self.sendNoAmp()
        else:
            await self.sendStateData(websocket, self.getCurrentState(channel))

    async def sendStateData(self, websocket, stateData):
        jsn = {"responseType": "state"}
        data = []
        for channel in stateData:
            data.append(channel.toDict())
        jsn["data"] = data
        await websocket.send(json.dumps(jsn))

    async def sendNoAmp(self):
        self.ampConnected = False
        jsn = {"responseType": "noAmp"}
        print("Sending no amp")
        for websocket in self.connections:
            await websocket.send(json.dumps(jsn))

    async def checkAmpPeriodically(self):
        while True:
            await asyncio.sleep(30)
            try:
                changedAmpData = self.amp.checkIfAmpChanged()
                if len(changedAmpData):
                    for websocket in self.connections:
                        await self.sendStateData(websocket, changedAmpData)
            except NoConnectionException:
                await self.sendNoAmp()


serialPort = sys.argv[1]
amp = Interface()
try:
    amp.connect(serialPort)
    server = WebSocketServer(amp)
    server.start()
finally:
    print("Disconnecting from serial")
    amp.disconnect()
