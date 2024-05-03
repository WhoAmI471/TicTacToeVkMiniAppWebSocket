import hashlib
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import desc
from models.leaderboard import Leaderboard
from config.database import SessionLocal
from typing import List


router = APIRouter()


# Define response models
class LeaderboardResponse(BaseModel):
    user_id: int
    position: int
    name: str
    last_name: str
    img_url: str
    score: int

# GET Request Method to retrieve all user statistics
@router.get("/leaderboard", tags=["Leaderboard"], response_model=List[LeaderboardResponse])
async def get_leaderboard():
    """
    Retrieve all user statistics.
    """
    db = SessionLocal()
    try:
        leaderboard = db.query(Leaderboard).all()
        return leaderboard
    finally:
        db.close()
    

# GET Request Method to retrieve user statistics
@router.get("/leaderboard/{user_id}", tags=["Leaderboard"], response_model=LeaderboardResponse)
async def get_user_position(user_id: int):
    """
    Retrieve user statistics by user_id.
    """
    db = SessionLocal()
    try:
        user_stat = db.query(Leaderboard).filter(Leaderboard.user_id == user_id).first()
        if user_stat is None:
            raise HTTPException(status_code=404, detail="User statistic not found")
        return user_stat
    finally:
        db.close()
    

# POST Request Method to update user statistics
@router.post("/leaderboard/{user_id}", tags=["Leaderboard"], response_model=LeaderboardResponse)
async def update_or_create_user_stats(user_id: int, stats: LeaderboardResponse):
    """
    Update or create user statistics by user_id.
    """
    db = SessionLocal()
    try:
        # Попытка найти пользователя в базе данных
        user_stat = db.query(Leaderboard).filter(Leaderboard.user_id == user_id).first()
        
        if user_stat is None:
            print('noooo')
            # Если пользователя нет, создаем нового
            new_user_stat = Leaderboard(user_id=user_id, position=stats.position, name=stats.name, last_name=stats.last_name, img_url=stats.img_url, score=stats.score)
            db.add(new_user_stat)
        
        db.commit()
        
        return JSONResponse(content={"message": "User statistics updated or created successfully"})
    finally:
        db.close()

    
# PUT Request Method to update specific user statistic
@router.put("/leaderboard/{user_id}", tags=["Leaderboard"], response_model=LeaderboardResponse)
async def update_specific_user_stat(user_id: int, stat_name: str, new_value: int):
    """
    Update a specific user statistic by user_id and stat_name.
    """
    db = SessionLocal()
    try:
        user_stat = db.query(Leaderboard).filter(Leaderboard.user_id == user_id).first()
        if user_stat is None:
            raise HTTPException(status_code=404, detail="User statistic not found")
        
        # Update specific user statistic based on stat_name
        if stat_name == "position":
            user_stat.position = new_value
        elif stat_name == "score":
            user_stat.score = new_value
        else:
            raise HTTPException(status_code=400, detail="Invalid stat_name")
        
        db.commit()
        
        return JSONResponse(content={"message": "Specific user statistic updated successfully"})
    finally:
        db.close()
   
# DELETE Request Method to delete a specific user statistic
@router.delete("/leaderboard/{user_id}", tags=["Leaderboard"], response_model=LeaderboardResponse)
async def delete_user_stat(user_id: int):
    """
    Delete a specific user statistic by user_id.
    """
    db = SessionLocal()
    try:
        user_stat = db.query(Leaderboard).filter(Leaderboard.user_id == user_id).first()
        if user_stat is None:
            raise HTTPException(status_code=404, detail="User statistic not found")
        
        db.delete(user_stat)
        db.commit()
        
        return JSONResponse(content={"message": "User statistic deleted successfully"})
    finally:
        db.close()

@router.put("/leaderboard-sort", tags=["Leaderboard"])
async def sort_leaderboard():
    """
    Sort users in leaderboard based on their scores.
    """
    db = SessionLocal()
    try:
        # Получаем список пользователей, отсортированный по убыванию количества очков
        all_user_stats = db.query(Leaderboard).order_by(desc(Leaderboard.score)).all()
        
        # Присваиваем новые позиции пользователям в порядке убывания количества очков
        for index, user_stat in enumerate(all_user_stats, start=1):
            user_stat.position = index
            db.add(user_stat)
        
        db.commit()
        
        # Собираем данные для JSON
        sorted_leaderboard = []
        for user_stat in all_user_stats:
            user_dict = {
                "position": user_stat.position,
                "user_id": user_stat.user_id,
                "score": user_stat.score,

                "name": user_stat.name,
                "last_name": user_stat.last_name,
                "img_url": user_stat.img_url,
            }
            sorted_leaderboard.append(user_dict)
        
        # Сортируем список по позициям
        sorted_leaderboard.sort(key=lambda x: x["position"])
        
        return sorted_leaderboard
    finally:
        db.close()


class PurchaseRequest(BaseModel):
    notification_type: str
    item: str = None
    status: str = None
    order_id: str = None
    sig: str

@router.post('/purchase')
async def purchase(request_data: PurchaseRequest):
    request_params = request_data.model_dump()

    # Проверяем подпись
    if calc_signature(request_params) == request_params['sig']:
        # Обрабатываем запрос
        if request_params['notification_type'] in ['get_item', 'get_item_test']:
            return handle_get_item(request_params)
        elif request_params['notification_type'] in ['order_status_change', 'order_status_change_test']:
            return handle_order_status_change(request_params)
    else:
        raise HTTPException(status_code=400, detail="Несовпадение переданной и вычисленной подписи")

# Вычисление подписи
def calc_signature(params):
    ACCESS_KEY = 'f748a91ff748a91ff748a91fe3f4597af2ff748f748a91f94dc0f4498292e74fec69d67'  # Ключ доступа приложения

    # Сортируем параметры
    keys = sorted(params.keys())

    # Формируем строку из пар 'параметр=значение'
    str_params = '&'.join([f"{k}={params[k]}" for k in keys if k != "sig"])
    str_params += ACCESS_KEY  # Добавляем ключ доступа

    # Вычисляем подпись
    calculated_signature = hashlib.md5(str_params.encode()).hexdigest()

    return calculated_signature

# Обработчик уведомления get_item
def handle_get_item(params):
    # Пример данных о товарах (предполагается, что saleItems - это словарь)
    saleItems = {
        "item_id_1": {"name": "Item 1", "price": 10},
        "item_id_2": {"name": "Item 2", "price": 20}
    }

    item_id = params.get("item")
    item = saleItems.get(item_id)

    # Возвращаем ответ
    if item:
        return {"response": item}
    else:
        raise HTTPException(status_code=404, detail="Товара не существует")

# Обработчик уведомления order_status_change
def handle_order_status_change(params):
    status = params.get("status")

    if status == 'chargeable':
        # Предоставляем товар в приложении
        # ...

        # Сохраняем информацию о заказе в приложении
        # ...

        # Формируем ответ
        app_order = 1  # Идентификатор заказа в приложении

        return {
            "response": {
                "order_id": params.get("order_id"),
                "app_order_id": app_order
            }
        }
    elif status == 'refund':
        # Обрабатываем возврат
        # ...
        pass
    else:
        raise HTTPException(status_code=400, detail="Ошибка в структуре данных")
