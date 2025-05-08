from fastapi import APIRouter;
from database.db import new_users_collection

router = APIRouter(prefix="/v2",tags=["API"])


@router.get('/users')
async def getusers():
    try:
        users_cursor = new_users_collection.find({})
        users = []
        for user in users_cursor:
            user['_id'] = str(user['_id'])  # Convert ObjectId to string
            users.append(user)
        return users
    except Exception as e:
        print("Error:", e)
        return {"error": "Failed to fetch users"}