# routes/add_friend.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from database.db import new_users_collection

router = APIRouter(prefix="/v2", tags=["User"])

class FriendRequest(BaseModel):
    user_id: str
    friend_username: str

@router.post("/user/add-friend")
def add_friend(request: FriendRequest):
    try:
        user_id = request.user_id
        friend_username = request.friend_username

        # Check both users exist
        user = new_users_collection.find_one({"userId": user_id})
        friend = new_users_collection.find_one({"handle": friend_username})
        #print(friend["_id"])
        if not user or not friend:
            raise HTTPException(status_code=404, detail="User or friend not found")

        # Add friend to user's friend list (if not already there)
        result = new_users_collection.update_one(
            {"userId": user_id},
            {"$addToSet": {"friends": friend["_id"]}}
        )

        return {
            
            "message": "Friend added successfully",
            "modified_count": result.modified_count
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
def serialize_friend(friend):
    return {
        "id": str(friend.get("_id")),
        "fullName": friend.get("fullName"),
        "profile": friend.get("profile"),
        "handle": friend.get("handle"),
    }

@router.get("/user/{user_id}/friends")
def get_user_friends(user_id: str):
    user = new_users_collection.find_one({"userId": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    friend_ids = user.get("friends", [])
    if not friend_ids:
        return {"friends": []}

    # Make sure all are ObjectId
    try:
        object_ids = [ObjectId(fid) if isinstance(fid, str) else fid for fid in friend_ids]
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid friend IDs format")

    friends = list(new_users_collection.find({"_id": {"$in": object_ids}}))

    serialized_friends = [serialize_friend(friend) for friend in friends]

    return {"friends": serialized_friends}
