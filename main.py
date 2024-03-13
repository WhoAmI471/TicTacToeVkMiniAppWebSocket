from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

app = FastAPI()

client_connections: Dict[int, WebSocket] = {}
opponents: Dict[int, int] = {}
client_ids_waiting_match: List[int] = []

winning_combos = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
    [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
    [0, 4, 8], [2, 4, 6]              # Diagonals
]

def check_win(field):
    return any(all(field[i] != "" and field[i] == field[j] == field[k] for i, j, k in combo) for combo in winning_combos)

def check_draw(field):
    return all(symbol == "X" or symbol == "O" for symbol in field)

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
    except WebSocketDisconnect:
        await close_client(websocket, client_id)

async def move_handler(result: dict, client_id: int):
    opponent_client_id = opponents[client_id]

    if check_win(result["field"]):
        for c_id in [client_id, opponent_client_id]:
            await client_connections[c_id].send_json({
                "method": "result",
                "message": f"{result['symbol']} win",
                "field": result["field"],
            })
        return

    if check_draw(result["field"]):
        for c_id in [client_id, opponent_client_id]:
            await client_connections[c_id].send_json({
                "method": "result",
                "message": "Draw",
                "field": result["field"],
            })
        return

    for c_id in [client_id, opponent_client_id]:
        await client_connections[c_id].send_json({
            "method": "update",
            "turn": "O" if result["symbol"] == "X" else "X",
            "field": result["field"],
        })

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