from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
import bcrypt
from datetime import datetime, timedelta
import jwt
import os
import uuid
from db import users_collection, licenses_collection

router = APIRouter(prefix="/auth", tags=["Auth"])

# Security settings
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# Models
class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class ActivateLicense(BaseModel):
    license_key: str

# Helper functions
def get_hardware_id():
    # Lấy MAC address của máy tính hiện tại làm Hardware ID
    return str(uuid.getnode())

def verify_password(plain_password: str, hashed_password: str):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency: Get current user
def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Không có quyền truy cập (Missing Token)")
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token không hợp lệ")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn hoặc không hợp lệ")
    
    user = users_collection.find_one({"email": email})
    if user is None:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại")
        
    # KICK CƠ CHẾ: Check hardware ID
    current_hw_id = get_hardware_id()
    if user.get("hardware_id") != current_hw_id:
        raise HTTPException(status_code=403, detail="Tài khoản này đang được đăng nhập ở một máy tính khác. Vui lòng đăng nhập lại để chiếm quyền.")
        
    return user

@router.post("/register")
async def register(user: UserCreate):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email này đã được đăng ký.")
        
    new_user = {
        "email": user.email,
        "password_hash": get_password_hash(user.password),
        "hardware_id": get_hardware_id(),
        "active_license": None,
        "created_at": datetime.utcnow()
    }
    
    users_collection.insert_one(new_user)
    return {"message": "Đăng ký thành công!"}

@router.post("/login")
async def login(user: UserLogin):
    db_user = users_collection.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng.")
        
    # Cập nhật lại hardware_id để chiếm quyền điều khiển (Kick máy cũ)
    new_hw_id = get_hardware_id()
    users_collection.update_one({"email": user.email}, {"$set": {"hardware_id": new_hw_id}})
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/activate")
async def activate_license(req: ActivateLicense, current_user=Depends(get_current_user)):
    # Nếu đã có bản quyền rồi thì không cần
    if current_user.get("active_license"):
        raise HTTPException(status_code=400, detail="Tài khoản của bạn đã được kích hoạt bản quyền.")
        
    # Tìm license trong DB
    license_doc = licenses_collection.find_one({"license_key": req.license_key})
    if not license_doc:
        raise HTTPException(status_code=404, detail="Mã kích hoạt không tồn tại.")
        
    if license_doc.get("status") == "used":
        raise HTTPException(status_code=400, detail="Mã kích hoạt này đã được sử dụng bởi người khác.")
        
    if license_doc.get("status") == "suspended":
        raise HTTPException(status_code=400, detail="Mã kích hoạt này đã bị khóa.")
        
    # Cập nhật License và User
    licenses_collection.update_one(
        {"_id": license_doc["_id"]},
        {"$set": {
            "status": "used",
            "used_by_email": current_user["email"],
            "activated_at": datetime.utcnow()
        }}
    )
    
    users_collection.update_one(
        {"email": current_user["email"]},
        {"$set": {"active_license": req.license_key}}
    )
    
    return {"message": "Kích hoạt bản quyền thành công! Chào mừng bạn đến với phiên bản PRO."}

@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    # Format lại để giấu password_hash
    return {
        "email": current_user["email"],
        "is_pro": current_user.get("active_license") is not None,
        "license_key": current_user.get("active_license")
    }
