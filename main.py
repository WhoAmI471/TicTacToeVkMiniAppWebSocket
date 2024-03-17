from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

app = FastAPI()

client_connections: Dict[int, WebSocket] = {}
opponents: Dict[int, int] = {}
client_ids_waiting_match: List[int] = []

async def match_clients(client_id: int):
    client_ids_waiting_match.append(client_id)

    if len(client_ids_waiting_match) < 2:
        return

    first_client_id = client_ids_waiting_match.pop(0)
    second_client_id = client_ids_waiting_match.pop(0)

    opponents[first_client_id] = second_client_id
    opponents[second_client_id] = first_client_id

    await client_connections[first_client_id].send_json({
        "method": "join",
        "symbol": "X",
        "turn": "X"
    })

    await client_connections[second_client_id].send_json({
        "method": "join",
        "symbol": "O",
        "turn": "X"
    })

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await websocket.accept()
    client_connections[client_id] = websocket

    await match_clients(client_id)

    try:
        while True:
            data = await websocket.receive_text()
            result = json.loads(data)
            if result["method"] == "move":
                await move_handler(result, client_id)
            if result["method"] == "opponentMove":
                await opponent_move_handler(result, client_id)
    except WebSocketDisconnect:
        await close_client(websocket, client_id)

async def opponent_move_handler(result: dict, client_id: int):
    opponent_client_id = opponents[client_id]
    # Отправляем обновление о ходе противнику
    opponent_websocket = client_connections[opponent_client_id]
    await opponent_websocket.send_json({
        "method": "opponentMove",
        "board": result["board"],  # номер доски
        "position": result["position"], # позиция на доске
        "turn": result["turn"],
    })

async def move_handler(result: dict, client_id: int):
    opponent_client_id = opponents[client_id]
    current_symbol = "X" if client_id in client_connections else "O"
    next_symbol = "O" if current_symbol == "X" else "X"

    # Ожидаем ход другого игрока, если это не его ход
    if current_symbol == "O":
        await client_connections[client_id].send_json({
            "method": "waiting",
            "message": "Waiting for opponent's move..."
        })
        return

async def close_client(websocket: WebSocket, client_id: int):
    await websocket.close()
    is_left_unmatched_client = client_id in client_ids_waiting_match

    if is_left_unmatched_client:
        client_ids_waiting_match.remove(client_id)
    else:
        opponent_client_id = opponents[client_id]
        await client_connections[opponent_client_id].send_json({
            "method": "left",
            "message": "opponent left",
        })