import asyncio
import audioop
import math
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription,RTCDataChannel

pcs = set()

async def offer(request):
    print("received offer request")
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    # Add default STUN server for ICE negotiation
    from aiortc import RTCConfiguration, RTCIceServer
    config = RTCConfiguration(iceServers=[])
    pc = RTCPeerConnection(configuration=config)
    pcs.add(pc)

    @pc.on("datachannel")
    def on_datachannel(channel: RTCDataChannel):

        if channel.label == "text":

            @channel.on("message")
            def on_text_message(msg: str) -> None:
                print("Text:", msg)
                asyncio.create_task(stream_text(channel, msg))

        elif channel.label == "control":
            @channel.on("message")
            def on_control_message(msg: str) -> None:
                print("Control:", msg)
                asyncio.create_task(stream_text(channel, msg))


    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.json_response(
        {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    )

async def stream_text(channel, prompt):
    for chunk in prompt.split():
        channel.send(chunk)
        await asyncio.sleep(0.1)
    channel.send("[done]")

async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

app = web.Application()
app.router.add_post("/offer", offer)
app.on_shutdown.append(on_shutdown)

web.run_app(app, port=8080)
