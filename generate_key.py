import os
import uuid
from datetime import datetime
from db import licenses_collection

def generate_license_key():
    # Format: KRILLIN-XXXX-XXXX-XXXX
    raw_uuid = str(uuid.uuid4()).upper().replace("-", "")
    key = f"KRILLIN-{raw_uuid[:4]}-{raw_uuid[4:8]}-{raw_uuid[8:12]}"
    
    license_doc = {
        "license_key": key,
        "status": "unused",
        "used_by_email": None,
        "created_at": datetime.utcnow()
    }
    
    licenses_collection.insert_one(license_doc)
    print("=========================================")
    print("✅ Đã tạo License Key thành công!")
    print(f"🔑 Key của bạn: {key}")
    print("=========================================")

if __name__ == "__main__":
    generate_license_key()
