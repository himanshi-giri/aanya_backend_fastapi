# routes/v2/Auth_routes.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from database.db import new_users_collection
import jwt as pyjwt
import random
import string
import os
import aiosmtplib
from email.message import EmailMessage

router = APIRouter(prefix="/v2/auth", tags=["Auth"])

ALGORITHM = "HS256"

SECRET_KEY = os.getenv("SECRET_KEY")
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = os.getenv("MAIL_PORT")
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")


# === Pydantic Schemas ===
class SignupRequest(BaseModel):
    userId: str
    fullName: str
    email: EmailStr
    password: str
    role: str
    handle: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyOTPRequest(BaseModel):  # Added for OTP verification
    email: EmailStr
    otp: str


class UserResponse(BaseModel):  # Added for /verify-otp
    userId: str
    email: EmailStr
    fullName: str


# --- Utility Functions ---
def generate_otp(length: int = 6) -> str:
    """Generates a random numeric OTP of the specified length."""
    characters = string.digits
    return "".join(random.choice(characters) for _ in range(length))


async def send_verification_email_otp(email: EmailStr, otp: str):
    """Sends an email containing the OTP for verification."""
    subject = "Verify your email address"
    body = f"""
    <html>
    <body>
        <div style="font-family: Arial, sans-serif;">
            <h1>Hii Vinay this side</h1>
            <p>Please use the following One-Time Password (OTP) to verify your email address:</p>
            <div style="font-size: 24px; font-weight: bold; color: #007bff;">{otp}</div>
            <p>This OTP is valid for 15 minutes.</p>
            <p>If you did not request this verification, please ignore this email.</p>
        </div>
    </body>
    </html>
    """

    message = EmailMessage()
    message["From"] = MAIL_FROM
    message["To"] = email
    message["Subject"] = subject
    message.set_content("This is an HTML email.")
    message.add_alternative(body, subtype="html")

    try:
        smtp = aiosmtplib.SMTP(hostname=MAIL_SERVER, port=int(MAIL_PORT), use_tls=True)
        await smtp.connect()
        await smtp.login(MAIL_USERNAME, MAIL_PASSWORD)
        await smtp.send_message(message)
        await smtp.quit()
    except Exception as e:
        print(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification email")





# === Routes ===
@router.post("/signup")
async def register_user(request: SignupRequest):
    try:
        # Check if user already exists
        if new_users_collection.find_one({"email": request.email}):
            raise HTTPException(
                status_code=400, detail="User with this email already exists"
            )

        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(
            minutes=15
        )  # OTP expires in 15 minutes

        # Create the user
        new_user = {
            "userId": request.userId,
            "fullName": request.fullName,
            "email": request.email,
            "password": request.password,  # Store the plain password temporarily
            "role": request.role,
            "handle":request.handle,
            "is_verified": False,  # Add is_verified field
            "otp": otp,  # Store the OTP
            "otp_expiry": otp_expiry,  # Store OTP expiry
            "createdAt": datetime.utcnow(),
        }

        new_users_collection.insert_one(new_user)

        await send_verification_email_otp(
            request.email, otp
        )  

        return {
            "message": f"OTP sent to {request.email}. Please verify within 15 minutes.",
            "userId": request.userId,
        }

    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/login")
async def login_user(request: LoginRequest):
    try:
        user = new_users_collection.find_one({"email": request.email})
        if not user or user["password"] != request.password:  # Check plain password
            raise HTTPException(
                status_code=401, detail="Invalid email or password"
            )

        if not user["is_verified"]:
            raise HTTPException(
                status_code=401, detail="Email not verified. Please verify your email."
            )

        token_payload = {
            "userId": user["userId"],
            "email": user["email"],
            "exp": datetime.utcnow() + timedelta(days=1),
        }

        session_token = pyjwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)

        return {
            "message": "Login successful",
            "userId": user["userId"],
            "email": user["email"],
            "fullName": user["fullName"],
            "token": session_token,
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print("Login error:", str(e))  # Add this line
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/verify-otp")
async def verify_otp(verification_data: VerifyOTPRequest):
    """
    Verifies the OTP entered by the user.
    """
    user = new_users_collection.find_one({"email": verification_data.email})
    if not user:
        raise HTTPException(
            status_code=444, detail="User not found with this email"
        )  # Changed to 444

    if user["otp"] != verification_data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if datetime.utcnow() > user["otp_expiry"]:
        raise HTTPException(
            status_code=408, detail="OTP has expired. Please request a new one."
        )  # Changed to 408

    new_users_collection.update_one(
        {"email": verification_data.email},
        {
            "$set": {
                "is_verified": True,
                "otp": None,
                "otp_expiry": None,
                "updated_at": datetime.utcnow(),
            }
        },
    )
    updated_user = new_users_collection.find_one(
        {"email": verification_data.email}
    )  # get the updated user

    return {
        "message": "Email verified successfully!",
        "user": {
            "userId": updated_user["userId"],  #  userId is already a string
            "email": updated_user["email"],
            "fullName": updated_user["fullName"],
        },  # Return user data
    }