#!/usr/bin/python3

import asyncio
import time
import json
import Hamlib

from websockets.asyncio.server import serve

async def hello(websocket):
    print("Connection from", websocket)
    #name = await websocket.recv()
    #print(f"<<< {name}")

    freq0 = None

    while True:
        freq = round(my_rig.get_freq() / 1000.0, 2)
        if freq != freq0:
            set_freq = freq + 0.750
            print(f">>> {freq} ({set_freq})")
            await websocket.send(str(set_freq))
            freq0 = freq
        time.sleep(0.2)

async def main():
    async with serve(hello, "localhost", 8765) as server:
        await server.serve_forever()

if __name__ == "__main__":
    Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_NONE)
    global my_rig
    my_rig = Hamlib.Rig(Hamlib.RIG_MODEL_NETRIGCTL)
    my_rig.set_conf("rig_pathname", "localhost:4532")
    #my_rig.set_conf("rig_pathname", "192.168.0.3:4532")
    my_rig.open()

    asyncio.run(main())
