import asyncio
import json
import aiohttp
import logging
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRecorder, MediaPlayer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

async def main():
    from aiortc import RTCConfiguration, RTCIceServer
    config = RTCConfiguration(iceServers=[])
    pc = RTCPeerConnection(configuration=config)
    channel1 = pc.createDataChannel("text")
    channel2 = pc.createDataChannel("control")
    

    @channel1.on("message")
    def on_message(message):
            print(f"Client text1: {message}")
            # Replace with your AI text pipeline; we just echo back streaming chunks
            #asyncio.create_task(stream_text(channel, message))


    @channel1.on("open")
    def on_open():
            logger.error("Data1 channel is open")
            channel1.send("hello world text")

    

    @channel2.on("message")
    def on_message(message):
            print(f"Client text2: {message}")
            # Replace with your AI text pipeline; we just echo back streaming chunks
            #asyncio.create_task(stream_text(channel, message))


    @channel2.on("open")
    def on_open():
            logger.error("Data2 channel is open")
            channel2.send("hello world message")



    logger.error("before creating the offer")


    offer = await pc.createOffer()
    logger.error("created offer, setting local description")
    await pc.setLocalDescription(offer)
    #print("SDK parameters ",pc.localDescription.sdp)
    print("----------------------------------------------")
    logger.error("after crating the offer")
    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8080/offer", json={
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        }) as resp:
            logger.error("received offer response")
            response = await resp.json()
            answer = RTCSessionDescription(sdp=response["sdp"], type=response["type"])
            await pc.setRemoteDescription(answer)


    logger.error("after starting the player")
    # Wait for some time to allow data channel communication
    await asyncio.sleep(20)
    logger.error("closing the connection")

    await pc.close()
    logger.error("after closing the connection")


asyncio.run(main())
