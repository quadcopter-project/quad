from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
import pyaudio
import wave
import time
from twisted.internet import reactor

# Audio server 
# recieve command on recording time 

class AudioServer:
    def __init__(self, host = "127.0.0.1", port=9000):
        self.host = host
        self.port = port
    class ServerProtocol(WebSocketServerProtocol):
    
        def onConnect(self, request):
            print("Client connecting: {}".format(request.peer))
    
        def onOpen(self):
            print("WebSocket connection open.")
    
        def onClose(self, wasClean, code, reason):
            print("WebSocket connection closed: {}".format(reason))
    
            """
            HEADER      MESSAGE 
            RecordNow     duration,path
            RecordAt    timedate, duration, path
            """
        def onMessage(self, payload, isBinary):
            if isBinary:
                print("Binary message received: {} bytes".format(len(payload)))
            else:
                message = payload.decode('utf8')
                print(f"Text message received: {message}")
                # parsing recieved message 
                msglist = message.strip().split(" ")
                header = msglist[0]

                match header:
                    case 'RecordNow':
                        data = msglist[1].split(",")
                        duration = int(data[0])
                        path = data[1]
                        self.factory.server.record_audio(duration,path)
                        
    def run(self):
        factory = WebSocketServerFactory(f"ws://{self.host}:{self.port}")
        factory.protocol = self.ServerProtocol
        factory.server = self
        
        reactor.listenTCP(self.port, factory)
        print(f"WebSocket server started on ws://{self.host}:{self.port}")
        reactor.run()
    
    def record_audio(self, duration, output_path):
        # Audio recording parameters
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        CHUNK = 1024

        # Initialize pyaudio()
        audio = pyaudio.PyAudio()

        # Opening stream
        stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
        #waiting for start up
        time.sleep(0.5)
        print(f"AudioServer::recording for duration {duration}")
        frames = []
        # record for specific time 
        for _ in range(0, int(RATE/CHUNK*duration)):
            data = stream.read(CHUNK)
            frames.append(data)

        print(f"AudioServer::recording finished.")

        # Stop Stream 
        stream.stop_stream()
        stream.close()
        audio.terminate()

        # Save the recorded data in lossless format 
        wf = wave.open(output_path, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

        print(f"Audio saved to {output_path}")

if __name__ == '__main__':
    server = AudioServer()
    server.run()
