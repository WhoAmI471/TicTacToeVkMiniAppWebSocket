from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
from routes.route import router
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Обновите это на список разрешенных источников, если это необходимо
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Добавляем метод OPTIONS
    allow_headers=["*"],
)

app.include_router(router)

client_connections: Dict[int, WebSocket] = {}
opponents: Dict[int, int] = {}
client_ids_waiting_match: List[int] = []
room_connections: Dict[str, Dict[int, WebSocket]] = {}

async def match_clients(client_id: int, room_id: str):
    if room_id == "0":
        client_ids_waiting_match.append(client_id)

        if len(client_ids_waiting_match) < 2:
            return

        first_client_id = client_ids_waiting_match.pop(0)
        second_client_id = client_ids_waiting_match.pop(0)

        opponents[first_client_id] = second_client_id
        opponents[second_client_id] = first_client_id

        # Отправляем идентификаторы клиентов друг другу
        await client_connections[first_client_id].send_json({
            "method": "join",
            "symbol": "X",
            "turn": "X",
            "opponent_id": second_client_id  # Добавляем идентификатор оппонента
        })

        await client_connections[second_client_id].send_json({
            "method": "join",
            "symbol": "O",
            "turn": "X",
            "opponent_id": first_client_id  # Добавляем идентификатор оппонента
        })
    else:
        # Для других комнат реализуйте логику сопоставления игроков по идентификатору комнаты
        pass

@app.websocket("/ws/{client_id}/{room_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int, room_id: str):
    # Проверяем, существует ли уже клиент с таким client_id
    if client_id in client_connections:
        await websocket.close()
        return

    await websocket.accept()
    client_connections[client_id] = websocket

    if room_id == "0":
        await match_clients(client_id, room_id)
    else:
        # Для других комнат реализуйте логику обработки
        pass

    try:
        while True:
            data = await websocket.receive_text()
            result = json.loads(data)
            if result["method"] == "move":
                await move_handler(result, client_id)
            if result["method"] == "opponentMove":
                await opponent_move_handler(result, client_id)
    except WebSocketDisconnect:
        await close_client(websocket, client_id, room_id)

async def opponent_move_handler(result: dict, client_id: int):
    opponent_client_id = opponents[client_id]
    opponent_websocket = client_connections[opponent_client_id]
    await opponent_websocket.send_json({
        "method": "opponentMove",
        "board": result["board"],
        "position": result["position"],
        "turn": result["turn"],
    })

async def move_handler(result: dict, client_id: int):
    opponent_client_id = opponents[client_id]
    current_symbol = "X" if client_id in client_connections else "O"
    next_symbol = "O" if current_symbol == "X" else "X"

    if current_symbol == "O":
        await client_connections[client_id].send_json({
            "method": "waiting",
            "message": "Waiting for opponent's move..."
        })
        return

async def close_client(websocket: WebSocket, client_id: int, room_id: str):
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

    if room_id in room_connections and client_id in room_connections[room_id]:
        del room_connections[room_id][client_id]
        if not room_connections[room_id]:
            del room_connections[room_id]
