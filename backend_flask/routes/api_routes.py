from tempfile import template
from fastapi import APIRouter, HTTPException, Form, UploadFile,Request
from database.db import models
from fastapi.responses import StreamingResponse ,JSONResponse
from helpers.Logger2 import Logger
import json
from typing import Dict, Any
from pathlib import Path

import json
import os
import traceback
from providers.ClaudeAI import ClaudeAI
from providers.ClaudeAI2 import ClaudeAI2

from providers.Gemini import GeminiAI
# models_file_path = Path("models.json")

claude_ai = ClaudeAI()
claude_ai_old = ClaudeAI2()
gemini_ai = GeminiAI()


is_llm_enabled = os.getenv("LLM_ENABLED") == "True"

router = APIRouter(prefix="/api", tags=["API"])


async def generate_ai_response(ai_provider, message, history, image, model):
    try:
        history = json.loads(history)
        
        if is_llm_enabled:
            ai_response = await ai_provider.get_data(
                system="You are an AI assistant.",
                data={
                    "message": message,
                    "history": history,
                    "image": image,
                    "model": model
                }
            )
        else:
            ai_response = {"role": "assistant", "content": [{"type": "text", "text": "Thank You for calling LLM"}]}
        
        return {"response": ai_response}
    
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
# api route for claude
@router.post("/generate_claude")
async def generate_claude(
    message: str = Form(...),
    history: str = Form("[]"),
    image: UploadFile = None,
    model: str = Form("claude-3")
):
    return await generate_ai_response(claude_ai, message, history, image, model)


# @router.post("/generate")
# async def generate():

#     return 

#api route for gemini 
@router.post("/gemini/{role}")
async def generate_gemini(
    role: str, request: Request
):
    """Handles Gemini API calls with correct formatting."""
    request_data = await request.form()
    history = request_data.get("history")
    model = request_data.get("model")
    system_prompt = claude_ai.get_system_prompt(role, request_data)
    # print(system_prompt)

    if isinstance(history, str):
        history = json.loads(history)

    # ✅ Call Gemini's function for streaming
    stream_generator = await gemini_ai.get_data_stream(system=system_prompt, data={
        "message": request_data.get("message"),
        "history": history,
        "temperature": request_data.get("temperature", 0.5),
        "image": request_data.get("image"),
        "model": model
    })
    
    if isinstance(stream_generator,dict):
        print("❌ stream_generator() returned None!")  # 🔴 ERROR: Function is failing early
        return JSONResponse(content={"error": "error ocuured in api (limit exceded or model is not present try changing model)"}, status_code=500)


    print("⚡ Returning StreamingResponse...")  

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


#api route for chatgpt
@router.post("/generate_chatgpt")
async def generate_gemini(
    message: str = Form(...),
    history: str = Form("[]"),
    image: UploadFile = None,
    model: str = Form("chatgpt-4")
):
    """Handles Gemini API calls with correct formatting."""
    return await generate_ai_response(gemini_ai, message, history, image, model)


@router.post("/claude/{role}")
async def stream_chat(role:str,request: Request):
    request_data = await request.form()

    history = request_data.get("history")
    model = request_data.get("model")
    system_prompt= claude_ai.get_system_prompt(role,request_data)

    if isinstance(history, str):
        history = json.loads(history)

    # ✅ Call the function from the module
    stream_generator = await claude_ai.get_data_stream(system=system_prompt, data={
        "message": request_data.get("message"),
        "history": history,
        "temperature": request_data.get("temperature", 0.5),
        "image": request_data.get("image"),
        "model": model
    })
    if stream_generator is None:
        print("❌ stream_generator() returned None!")  # 🔴 ERROR: Function is failing early
        return JSONResponse(content={"error": "Stream generator not created"}, status_code=500)

    print("⚡ Returning StreamingResponse...")  #
    
    return StreamingResponse(stream_generator(), media_type="text/event-stream")
    


@router.post("/generate_claude/{role}")
async def generate_claude(role: str, request: Request):
    """Generates Claude responses based on user role and form data."""

    form_data: Dict[str, Any] = await request.form()

    message = form_data.get("message")
    history = form_data.get("history", "[]")  # Default to "[]" if not present
    image = form_data.get("image")  # Will be an UploadFile or None
    model = form_data.get("model", "claude-3")
    data_key=form_data.get("data_key") #default the model.
    
    try:
        import json #moved import inside try block.
        history = json.loads(history)
        
        system_prompt= claude_ai.get_system_prompt(role,form_data)
        
        
        if is_llm_enabled :
            ai_response = await ClaudeAI().get_data(
                system=system_prompt,
                data={
                    "message": message,
                    "history": history,
                    "image": image,
                      "model":model  # UploadFile object from FastAPI
                }
            )
        else:
            ai_response={"role": "assistant", "content": [{"type":"text","text":"Thank You for calling LLM"}]}

        
        # Example:
        
        
        return {"response": ai_response}

    except json.JSONDecodeError:
        return {"error": "Invalid JSON in history"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/initial_message")
async def get_initial_message(data_key: str = None,title: str = None):
    
        print(title)
        filepath = f"initial_messages/{data_key}.json" if data_key else "initial_messages/initial_message.json"
        print(filepath)
        if os.path.exists(filepath):
            with open(filepath, "r") as file:
                initial_message = json.load(file)
                initial_message["content"][0]["text"] = initial_message["content"][0]["text"].format(title= title)
                print(initial_message)
        return initial_message

                # logger.info(msg)


@router.get("/get_model")
async def get_available_model():
    try:

        # print(models)
        model_list = models.find({}, {"_id": 0}).to_list(length=None) # Exclude _id from response
        # print(model_list)
        return model_list
        # Read and load the JSON file
        # with open(models_file_path, "r") as f:
        #     models = json.load(f)
        # return {"gemini-1.5-pro"}

        # return models  # Return the loaded models from the JSON file
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
