import websocket

def send_message_and_quit(url, message):
    try:
        # Connect to the WebSocket server
        ws = websocket.WebSocket()
        ws.connect(url)
        
        # Send the message
        ws.send(message)
        
        # Close the connection
        ws.close()
        
        print("Message sent successfully and connection closed.")
    except Exception as e:
        print(f"An error occurred: {e}")
# Usage
websocket_url = "ws://localhost:9000"
message = "RecordNow 10,./test.wav"

send_message_and_quit(websocket_url, message)
