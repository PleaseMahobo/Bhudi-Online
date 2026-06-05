export function createSocket(deviceId: number, onMessage: (data: any) => void) {
  const ws = new WebSocket(`ws://localhost:8000/ws/${deviceId}`);

  ws.onmessage = (event) => {
    onMessage(JSON.parse(event.data));
  };

  return ws;
}