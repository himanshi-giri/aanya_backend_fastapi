from h11 import Request
from fastapi import APIRouter, HTTPException, UploadFile, File ,Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import os

UPLOAD_DIR = "uploads"

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload")
async def upload_file(request:Request, file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        print(request.base_url)
        return {"filename": file.filename, "url": f"{request.base_url}/uploads/{file.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/assets/{filepath:path}")
async def serve_assets(filepath: str):
    file_path = f"assets/{filepath}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="File not found")

@router.post("/upload-image/")
async def upload_image(request:Request, file: UploadFile = File(...)):
    
    try:
        print(file)
        # Save the file in the "uploads" directory
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR) 
        new_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}{os.path.splitext(file.filename)[1]}"

        file_path = os.path.join(UPLOAD_DIR, new_filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        print(request.base_url)
        # Generate a URL to access the file
        file_url = f"{request.base_url}uploads/{new_filename}"

        return JSONResponse(content={"filename": file.filename, "url": file_url})
    
    except Exception as e:
        return JSONResponse(content={"error": str(e) + "here"}, status_code=500)

