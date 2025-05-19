from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from pydantic import BaseModel
import os
import fitz
import google.generativeai as genai
from datetime import datetime
import base64
from typing import Optional
import random

from database.db import db


router = APIRouter(prefix="/doubt", tags=["Doubt Solver"])

# Load environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Pydantic models
class TextRequest(BaseModel):
    text: str
    mode: Optional[str] = "homework"  # Default to "homework" if not specified
    chat_history: Optional[list[str]] = []

class SolutionResponse(BaseModel):
    solution: str
    
# List of follow-up questions based on subject areas
follow_up_questions = {
    "math": [
        "Would you like to see a different approach to solve this problem?",
        "Do you understand how we applied the integration formula here?",
        "Should I explain any specific step in more detail?",
        "Would you like to try a similar problem to practice this concept?",
        "Is there a specific part of the solution that's confusing you?"
    ],
    "physics": [
        "Do you understand how we applied conservation of energy in this problem?",
        "Would you like me to explain the free-body diagram in more detail?",
        "Should we go through another example to reinforce this concept?",
        "Is there a specific formula or principle you'd like me to explain further?",
        "Would you like to see a real-world application of this concept?"
    ],
    "chemistry": [
        "Do you understand how we balanced this chemical equation?",
        "Would you like me to explain the mechanism of this reaction in more detail?",
        "Should I clarify anything about the molecular structure?",
        "Would you like to see how this concept applies in laboratory settings?",
        "Is there anything specific about the periodic trends that's unclear?"
    ],
    "general": [
        "Do you have any other questions about this topic?",
        "Would you like me to explain anything else?",
        "Is there a specific part of the explanation that wasn't clear?",
        "Would you like to explore this concept further?",
        "Should I give you some practice problems to test your understanding?"
    ]
}

# Helper function to generate solution using Gemini API
async def generate_solution(prompt, file_content=None, file_type=None, subject_hint="general", mode="homework"):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare content parts based on what's available
        content_parts = [prompt]
        
        # Add file content if available
        if file_content and file_type:
            if file_type.startswith('image/'):
                # For images, we need to handle them differently
                content_parts.append({
                    "mime_type": file_type,
                    "data": base64.b64encode(file_content).decode('utf-8')
                })
            else:
                # For text documents, just add the content
                if isinstance(file_content, bytes):
                    try:
                        text_content = file_content.decode('utf-8')
                        content_parts.append(f"Document content: {text_content}")
                    except UnicodeDecodeError:
                        content_parts.append("Unable to decode document content")
                else:
                    content_parts.append(f"Document content: {file_content}")
        
        # Determine the subject based on the prompt content
        if "math" in prompt.lower() or "calculate" in prompt.lower() or "equation" in prompt.lower() or "integral" in prompt.lower():
            subject = "math"
        elif "physics" in prompt.lower() or "force" in prompt.lower() or "motion" in prompt.lower() or "energy" in prompt.lower():
            subject = "physics"
        elif "chemistry" in prompt.lower() or "reaction" in prompt.lower() or "molecule" in prompt.lower() or "compound" in prompt.lower():
            subject = "chemistry"
        else:
            subject = "general"
            
        # Select a random follow-up question from the appropriate category
        follow_up = random.choice(follow_up_questions[subject])
        
        # Create an enhanced prompt based on the selected mode
        if mode == "stepbystep":
            # Step by Step Doubt Clearing mode
            enhanced_prompt = f"""{prompt}
You are a Tutor for K-12 students. You are patient and always eager to help students learn. Students come to you when they get stuck with a problem.

DO NOT reveal the complete solution to any problem. Instead, break the problem into small steps and guide the student through ONLY THE NEXT STEP.

For the current step:
1. Present ONLY ONE step (the next logical step) and ask the student a leading question.
2. Give just enough information to help the student figure out this step on their own.
3. Offer a hint if needed, but don't solve it for them.

Your response should be focused only on the immediate next step the student should take.

Encourage the student to think critically and work through the problems on their own.
Your role is to facilitate learning, not provide answers.

You possess deep and accurate knowledge of Math, Physics, Chemistry, Biology, and Social Science as taught under CBSE and ICSE boards. 
You also have expert-level knowledge of the syllabus required for competitive exams like IIT-JEE and NEET.

IMPORTANT: Never reveal the final solution or multiple steps at once.Make sure to provide only a single step at a time.

End with a question like: "What do you think the next step should be?" or "{follow_up}"
"""
        else:
            # Homework Help mode (complete solution)
            enhanced_prompt = f"""{prompt}
You are a Tutor for K-12 students. For Homework Help mode, your goal is to provide a complete, comprehensive solution with all steps clearly explained.

Please:
1. Use clear, step-by-step explanations with proper academic notation.
2. Break down complex processes into logical steps.
3. Include all necessary formulas, equations, and calculations.
4. Make sure every part of the solution is thoroughly explained.
5. Show all work and reasoning.

You possess deep and accurate knowledge of Math, Physics, Chemistry, Biology, and Social Science as taught under CBSE and ICSE boards.
You also have expert-level knowledge of the syllabus required for competitive exams like IIT-JEE and NEET.

End with a natural follow-up question like: "{follow_up}"
"""
        
        content_parts[0] = enhanced_prompt
        
        response = model.generate_content(
            content_parts,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 2048,
            }
        )
        
        # Store the solution in MongoDB
        solution_doc = {
            "prompt": prompt,
            "solution": response.text,
            "timestamp": datetime.now(),
            "subject": subject,
            "mode": mode
        }
        db.solutions_collection.insert_one(solution_doc)
        
        return response.text
    except Exception as e:
        print(f"Error generating solution: {e}")
        return f"Sorry, I couldn't generate a solution. Error: {str(e)}"

@router.post("/solve-text", response_model=SolutionResponse)
async def solve_text(request: TextRequest):
    """
    Process a text query and generate a solution based on the selected mode
    """
    try:
        formatted_history = "\n".join(chat for chat in request.chat_history) if request.chat_history else ""
        prompt = f"""
You are a helpful and knowledgeable AI tutor. Use the following conversation history to understand the user's context.

Conversation history:
{formatted_history}

Now answer this question:
{request.text}

Respond clearly using correct academic notation. Avoid HTML tags.
"""
        # Pass the mode to generate_solution
        solution = await generate_solution(prompt, mode=request.mode)
        return SolutionResponse(solution=solution)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    mode: str = Form(default="homework")  # Add mode parameter with default value
):
    try:
        # Read file content
        content = await file.read()
        
        # Store file in MongoDB GridFS 
        file_id = db.fs.put(
            content,
            filename=file.filename,
            content_type=file.content_type
        )
        
        # Store file metadata
        file_metadata = {
            "grid_fs_id": str(file_id),
            "filename": file.filename,
            "content_type": file.content_type,
            "mode": mode,  # Store the mode in metadata
            "timestamp": datetime.now()
        }
        
        db.uploads_collection.insert_one(file_metadata)
        
        extracted_text = ""
        if file.content_type == "application/pdf":
            extracted_text = await extract_text_from_pdf(content)
        elif file.content_type.startswith("text/"):
            extracted_text = content.decode("utf-8")
        else:
            extracted_text = "Unsupported file type for text extraction."

        # Generate solution based on file content and mode
        prompt = f"Please provide a solution for this document:\n{extracted_text}"
        solution = await generate_solution(prompt, content, file.content_type, mode=mode)
        
        return {"solution": solution}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def extract_text_from_pdf(file_bytes: bytes) -> str:
    text = ""
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page_num, page in enumerate(doc, start=1):
                text += page.get_text()
                print(f"Page {page_num} extracted text: {text[:200]}")  # Debugging: check extracted text from each page
    except Exception as e:
        print(f"PDF extraction error: {e}")
        text = "Failed to extract text from the PDF."
    return text
       
@router.post("/upload-image")
async def upload_image(
    image: UploadFile = File(...),
    mode: str = Form(default="homework")  # Add mode parameter with default value
):
    try:
        # Check if the file is actually an image
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image content
        image_content = await image.read()
        
        # Store image in MongoDB GridFS
        file_id = db.fs.put(
            image_content,
            filename=image.filename,
            content_type=image.content_type
        )
        
        # Store image metadata
        image_metadata = {
            "grid_fs_id": str(file_id),
            "filename": image.filename,
            "content_type": image.content_type,
            "mode": mode,  # Store the mode in metadata
            "timestamp": datetime.now()
        }
        
        db.uploads_collection.insert_one(image_metadata)
        
        # Generate solution based on image and mode
        prompt = "Please analyze the provided image and explain the solution in a clear manner. Start by identifying what is given and what needs to be found. Then outline the method or concept used to solve it. Use correct academic notation and terminology (e.g., x², ∫, Δt, moles, sin(θ), etc.), and avoid unnecessary special characters or HTML tags."
        solution = await generate_solution(prompt, image_content, image.content_type, "math", mode=mode)
        return {"solution": solution}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-voice")
async def send_voice(
    voice: UploadFile = File(...),
    mode: str = Form(default="homework")  # Add mode parameter with default value
):
    try:
        # Read voice content
        voice_content = await voice.read()
        
        # Store voice in MongoDB GridFS
        file_id = db.fs.put(
            voice_content,
            filename=voice.filename,
            content_type=voice.content_type
        )
        
        # Store voice metadata
        voice_metadata = {
            "grid_fs_id": str(file_id),
            "filename": voice.filename,
            "content_type": voice.content_type,
            "mode": mode,  # Store the mode in metadata
            "timestamp": datetime.now()
        }
        
        db.uploads_collection.insert_one(voice_metadata)
        
        # For voice input, placeholder response
        # In a production environment, you would integrate with a speech-to-text service
        base_prompt = "I've received your voice input. Currently, the system is using a placeholder response. In a production environment, we would use speech-to-text conversion to process your voice input."
        
        if mode == "stepbystep":
            solution = f"{base_prompt} I'll guide you through this problem one step at a time. Let's start with the first step. What problem are you trying to solve?"
        else:
            solution = f"{base_prompt} I'll provide a complete solution to your problem. Please describe the problem you need help with."
            
        return {"solution": solution}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Improved solve-image-text endpoint to handle image+text combinations with mode
@router.post("/solve-image-text")
async def solve_image_text(
    image: UploadFile = File(...),
    query: str = Form(default=""),  # Optional query
    mode: str = Form(default="homework")  # Add mode parameter with default value
):
    try:
        # Debug output
        print(f"Received image: {image.filename}, content type: {image.content_type}")
        print(f"Received query: {query}")
        print(f"Mode selected: {mode}")
        
        # Check file is an image
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read image content
        image_content = await image.read()
        
        # Save to MongoDB
        file_id = db.fs.put(
            image_content,
            filename=image.filename,
            content_type=image.content_type
        )
        
        db.uploads_collection.insert_one({
            "grid_fs_id": str(file_id),
            "filename": image.filename,
            "content_type": image.content_type,
            "query": query,
            "mode": mode,  # Store the mode in metadata
            "timestamp": datetime.now()
        })

        # Improved prompt handling for different scenarios
        base_prompt = "Please analyze the provided image and explain the solution. Start by identifying what is given and what needs to be found. Then outline the method or concept used to solve it. Use correct academic notation and terminology (e.g., x², ∫, Δt, moles, sin(θ), etc.), and avoid unnecessary special characters or HTML tags."
        
        # If query exists, append it to the prompt
        if query.strip():
            prompt = f"{base_prompt} The user has asked: {query}"
        else:
            # This ensures image-only submissions work properly
            prompt = f"{base_prompt} Solve the problem shown in this image."

        # Determine subject from image/query context for better follow-up questions
        subject_hint = "math"  # Default for mathematical images
        if "chemistry" in query.lower() or "molecule" in query.lower() or "reaction" in query.lower():
            subject_hint = "chemistry"
        elif "physics" in query.lower() or "force" in query.lower() or "motion" in query.lower():
            subject_hint = "physics"

        # Generate answer from Gemini with image, text, and mode
        solution = await generate_solution(prompt, image_content, image.content_type, subject_hint, mode=mode)

        return {"solution": solution}
    except Exception as e:
        print(f"Error in solve-image-text: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# This can be used for testing the API without a file upload
@router.post("/test-query")
async def test_query(
    query: str = Form(...),
    mode: str = Form(default="homework")  # Add mode parameter with default value
):
    solution = await generate_solution(query, mode=mode)
    return {"solution": solution}