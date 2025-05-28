from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File
from pydantic import BaseModel, EmailStr
from typing import Optional
from database.db import new_users_collection
from datetime import datetime
import jwt as pyjwt
import os
import base64
from io import BytesIO

router = APIRouter(prefix="/v2/profile", tags=["Profile"])

ALGORITHM = "HS256"
SECRET_KEY = os.getenv("SECRET_KEY")

# === Pydantic Schemas ===
class UserUpdate(BaseModel):
    fullName: Optional[str] = None
    email: Optional[EmailStr] = None
    school: Optional[str] = None
    city: Optional[str] = None
    board: Optional[str] = None
    grade: Optional[str] = None
    contactNumber: Optional[str] = None
    profilePhoto: Optional[str] = None

class UserDetail(BaseModel):
    userId: str
    fullName: str
    email: EmailStr
    role: str
    handle: Optional[str] = None
    is_verified: bool
    createdAt: datetime
    school: Optional[str] = None
    city: Optional[str] = None
    board: Optional[str] = None
    grade: Optional[str] = None
    contactNumber: Optional[str] = None
    profilePhoto: Optional[str] = None

class ChangePassword(BaseModel):
    oldPassword: str
    newPassword: str

# --- Dependency for Authentication ---
def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = auth_header.split(" ")[1]
    try:
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# === Routes ===
@router.get("/user", response_model=UserDetail)
async def get_user_details(user=Depends(get_current_user)):
    try:
        user_id = user["userId"]
        userDetail = new_users_collection.find_one({"userId": user_id})
        if not userDetail:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "userId": userDetail["userId"],
            "fullName": userDetail["fullName"],
            "email": userDetail["email"],
            "role": userDetail["role"],
            "handle": userDetail.get("handle"),
            "is_verified": userDetail["is_verified"],
            "createdAt": userDetail["createdAt"],
            "school": userDetail.get("school"),
            "city": userDetail.get("city"),
            "board": userDetail.get("board"),
            "grade": userDetail.get("grade"),
            "contactNumber": userDetail.get("contactNumber"),
            "profilePhoto": userDetail.get("profilePhoto")
        }
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update-profile", response_model=UserDetail)
async def update_user_profile(update_data: UserUpdate, user=Depends(get_current_user)):
    try:
        user_id = user["userId"]
        user = new_users_collection.find_one({"userId": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prepare update data, excluding None values
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        if not update_dict:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        # Add updated_at timestamp
        update_dict["updated_at"] = datetime.utcnow()

        # Update the user document
        result = new_users_collection.update_one(
            {"userId": user_id},
            {"$set": update_dict}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made to the profile")

        # Fetch the updated user document
        updated_user = new_users_collection.find_one({"userId": user_id})
        return {
            "userId": updated_user["userId"],
            "fullName": updated_user["fullName"],
            "email": updated_user["email"],
            "role": updated_user["role"],
            "handle": updated_user.get("handle"),
            "is_verified": updated_user["is_verified"],
            "createdAt": updated_user["createdAt"],
            "school": updated_user.get("school"),
            "city": updated_user.get("city"),
            "board": updated_user.get("board"),
            "grade": updated_user.get("grade"),
            "contactNumber": updated_user.get("contactNumber"),
            "profilePhoto": updated_user.get("profilePhoto")
        }
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/upload-photo")
async def upload_profile_photo(file: UploadFile = File(...), user=Depends(get_current_user)):
    try:
        user_id = user["userId"]
        user = new_users_collection.find_one({"userId": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Validate file type
        if file.content_type not in ["image/jpeg", "image/png"]:
            raise HTTPException(status_code=400, detail="Only JPEG or PNG images are allowed")

        # Read and encode the image as base64
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode("utf-8")
        mime_type = file.content_type
        base64_string = f"data:{mime_type};base64,{base64_image}"

        # Update the user document with the base64 image
        result = new_users_collection.update_one(
            {"userId": user_id},
            {
                "$set": {
                    "profilePhoto": base64_string,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made to the profile photo")

        # Fetch the updated user document
        updated_user = new_users_collection.find_one({"userId": user_id})
        return {
            "message": "Profile photo uploaded successfully",
            "profilePhoto": updated_user.get("profilePhoto")
        }
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/change-password")
async def change_password(password_data: ChangePassword, user=Depends(get_current_user)):
    try:
        user_id = user["userId"]
        user_detail = new_users_collection.find_one({"userId": user_id})
        if not user_detail:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify old password (plain text)
        if password_data.oldPassword != user_detail.get("password"):
            raise HTTPException(status_code=400, detail="Incorrect old password")

        # Validate new password
        if len(password_data.newPassword) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

        # Update password (plain text)
        result = new_users_collection.update_one(
            {"userId": user_id},
            {
                "$set": {
                    "password": password_data.newPassword,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made to the password")

        return {"message": "Password changed successfully"}
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete-account")
async def delete_account(user=Depends(get_current_user)):
    try:
        user_id = user["userId"]
        result = new_users_collection.delete_one({"userId": user_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "Account deleted successfully"}
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
  