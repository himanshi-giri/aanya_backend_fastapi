from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from pydantic import BaseModel
import os
import fitz
import google.generativeai as genai
from datetime import datetime
import base64
from typing import Optional
import random
import speech_recognition as sr
import io
import tempfile
from pydub import AudioSegment
import re
from fastapi.responses import JSONResponse

from database.db import db , fs


router = APIRouter(prefix="/doubt", tags=["Doubt Solver"])

# Load environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Pydantic models
class TextRequest(BaseModel):
    text: str
    mode: Optional[str] = "stepbystep"  
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

# Helper function to convert audio to text using speech recognition
async def convert_audio_to_text(audio_content: bytes, content_type: str) -> str:
    """
    Convert audio file to text using speech recognition
    """
    try:
        recognizer = sr.Recognizer()
        
        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            # Convert audio to WAV format if needed
            if content_type in ["audio/wav", "audio/wave"]:
                temp_audio.write(audio_content)
            else:
                # Convert other audio formats to WAV using pydub
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_content))
                audio_segment.export(temp_audio.name, format="wav")
            
            temp_audio.flush()
            
            # Read the audio file with speech recognition
            with sr.AudioFile(temp_audio.name) as source:
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                # Record the audio
                audio_data = recognizer.record(source)
                
                try:
                    # Use Google's speech recognition
                    text = recognizer.recognize_google(audio_data)
                    return text
                except sr.UnknownValueError:
                    return "Could not understand the audio clearly"
                except sr.RequestError as e:
                    print(f"Speech recognition request error: {e}")
                    # Fallback to whisper or other services if needed
                    return "Audio processing temporarily unavailable"
        
        # Clean up temp file
        os.unlink(temp_audio.name)
        
    except Exception as e:
        print(f"Error converting audio to text: {e}")
        return "Failed to process audio input"

# Helper function to generate solution using Gemini API
async def generate_solution(prompt, file_content=None, file_type=None, subject_hint="general", mode="stepbystep"):
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
        if not request.mode or request.mode not in ["stepbystep", "homework"]:
           request.mode = "stepbystep"
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
    mode: str = Form(default="stepbystep")  # Add mode parameter with default value
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
    mode: str = Form(default="stepbystep")  # Add mode parameter with default value
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
    mode: str = Form(default="stepbystep")  # Add mode parameter with default value
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
        
        # Convert voice to text
        transcribed_text = await convert_audio_to_text(voice_content, voice.content_type)
        
        # Generate solution based on transcribed text and mode
        if transcribed_text and transcribed_text not in ["Could not understand the audio clearly", "Audio processing temporarily unavailable", "Failed to process audio input"]:
            prompt = f"The user asked via voice: {transcribed_text}"
            solution = await generate_solution(prompt, mode=mode)
        else:
            solution = f"I received your voice input but had trouble understanding it clearly. {transcribed_text}. Please try speaking clearly or use text input instead."
            
        return {"solution": solution, "transcribed_text": transcribed_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Improved solve-image-text endpoint to handle image+text combinations with mode
@router.post("/solve-image-text")
async def solve_image_text(
    image: UploadFile = File(...),
    query: str = Form(default=""),  # Optional query
    mode: str = Form(default="stepbystep")  # Add mode parameter with default value
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

# NEW ENDPOINT: Live Camera Voice Assistance
def convert_math_for_speech(text):
    """
    Convert mathematical expressions to speech-friendly format
    """
    # Dictionary for common mathematical symbols and expressions
    math_replacements = {
        # Superscripts and powers
        '²': ' square',
        '³': ' cube',
        '⁴': ' to the fourth power',
        '⁵': ' to the fifth power',
        '⁶': ' to the sixth power',
        '⁷': ' to the seventh power',
        '⁸': ' to the eighth power',
        '⁹': ' to the ninth power',
        '¹⁰': ' to the tenth power',
        
        # Subscripts
        '₁': ' sub 1',
        '₂': ' sub 2',
        '₃': ' sub 3',
        '₄': ' sub 4',
        '₅': ' sub 5',
        '₆': ' sub 6',
        '₇': ' sub 7',
        '₈': ' sub 8',
        '₉': ' sub 9',
        '₀': ' sub 0',
        
        # Greek letters
        'α': 'alpha',
        'β': 'beta',
        'γ': 'gamma',
        'δ': 'delta',
        'ε': 'epsilon',
        'ζ': 'zeta',
        'η': 'eta',
        'θ': 'theta',
        'ι': 'iota',
        'κ': 'kappa',
        'λ': 'lambda',
        'μ': 'mu',
        'ν': 'nu',
        'ξ': 'xi',
        'π': 'pi',
        'ρ': 'rho',
        'σ': 'sigma',
        'τ': 'tau',
        'υ': 'upsilon',
        'φ': 'phi',
        'χ': 'chi',
        'ψ': 'psi',
        'ω': 'omega',
        
        # Mathematical operators
        '×': ' times ',
        '÷': ' divided by ',
        '±': ' plus or minus ',
        '∓': ' minus or plus ',
        '≤': ' less than or equal to ',
        '≥': ' greater than or equal to ',
        '≠': ' not equal to ',
        '≈': ' approximately equal to ',
        '∞': ' infinity ',
        '∫': ' integral of ',
        '∑': ' sum of ',
        '√': ' square root of ',
        '∛': ' cube root of ',
        '∜': ' fourth root of ',
        '∂': ' partial derivative of ',
        '∆': ' delta ',
        '∇': ' nabla ',
        
        # Fractions
        '½': ' one half',
        '⅓': ' one third',
        '⅔': ' two thirds',
        '¼': ' one quarter',
        '¾': ' three quarters',
        '⅕': ' one fifth',
        '⅖': ' two fifths',
        '⅗': ' three fifths',
        '⅘': ' four fifths',
        '⅙': ' one sixth',
        '⅚': ' five sixths',
        '⅛': ' one eighth',
        '⅜': ' three eighths',
        '⅝': ' five eighths',
        '⅞': ' seven eighths',
    }
    
    # Apply basic symbol replacements
    speech_text = text
    for symbol, replacement in math_replacements.items():
        speech_text = speech_text.replace(symbol, replacement)
    
    # Handle x^n patterns (x to the power of n)
    speech_text = re.sub(r'([a-zA-Z])\^(\d+)', r'\1 to the power of \2', speech_text)
    speech_text = re.sub(r'([a-zA-Z])\^(\([^)]+\))', r'\1 to the power of \2', speech_text)
    
    # Handle x^2, y^2 etc specifically as "squared"
    speech_text = re.sub(r'([a-zA-Z])\^2\b', r'\1 squared', speech_text)
    speech_text = re.sub(r'([a-zA-Z])\^3\b', r'\1 cubed', speech_text)
    
    # Handle (expression)^2 patterns
    speech_text = re.sub(r'\(([^)]+)\)\^2', r'(\1) squared', speech_text)
    speech_text = re.sub(r'\(([^)]+)\)\^3', r'(\1) cubed', speech_text)
    speech_text = re.sub(r'\(([^)]+)\)\^(\d+)', r'(\1) to the power of \2', speech_text)
    
    # Handle fractions a/b
    speech_text = re.sub(r'(\d+)/(\d+)', r'\1 over \2', speech_text)
    speech_text = re.sub(r'([a-zA-Z]+)/([a-zA-Z]+)', r'\1 over \2', speech_text)
    
    # Handle trigonometric functions
    trig_functions = {
        'sin': 'sine',
        'cos': 'cosine', 
        'tan': 'tangent',
        'cot': 'cotangent',
        'sec': 'secant',
        'cosec': 'cosecant',
         'sinA':'sine A',
        'cosA':'cosine A',
        'tanA':'tangent A',
        'sinB':'sine B',
        'cosB':'cosine B',
        'tanB':'tangent B',
        'arcsin': 'arc sine',
        'arccos': 'arc cosine',
        'arctan': 'arc tangent',
        'sinh': 'hyperbolic sine',
        'cosh': 'hyperbolic cosine',
        'tanh': 'hyperbolic tangent',
    }
    
    for func, spoken in trig_functions.items():
        speech_text = re.sub(rf'\b{func}\b', spoken, speech_text, flags=re.IGNORECASE)
    
    # Handle logarithms
    speech_text = re.sub(r'\blog\b', 'logarithm', speech_text, flags=re.IGNORECASE)
    speech_text = re.sub(r'\bln\b', 'natural logarithm', speech_text, flags=re.IGNORECASE)
    
    # Handle common mathematical expressions
    speech_text = re.sub(r'\bf\(x\)', 'f of x', speech_text)
    speech_text = re.sub(r'\bg\(x\)', 'g of x', speech_text)
    speech_text = re.sub(r'\bh\(x\)', 'h of x', speech_text)
    speech_text = re.sub(r'f\'', 'f prime', speech_text)
    speech_text = re.sub(r'g\'', 'g prime', speech_text)
    
    # Handle chemical formulas (common ones)
    chemistry_replacements = {
        'H₂O': 'H 2 O',
        'CO₂': 'C O 2',
        'O₂': 'O 2',
        'N₂': 'N 2',
        'H₂SO₄': 'H 2 S O 4',
        'NaCl': 'N a C l',
        'CaCO₃': 'C a C O 3'
    }
    
    for formula, spoken in chemistry_replacements.items():
        speech_text = speech_text.replace(formula, spoken)
    
    # Clean up multiple spaces
    speech_text = re.sub(r'\s+', ' ', speech_text).strip()
    
    return speech_text

def create_dual_response(solution, mode="stepbystep"):
    """
    Create both display version and speech version of the response
    """
    # Original solution for display (with proper mathematical notation)
    display_solution = solution
    
    # Convert for speech synthesis
    speech_solution = convert_math_for_speech(solution)
    
    return {
        "display": display_solution,
        "speech": speech_solution
    }

@router.post("/solve-live-camera-voice")
async def solve_live_camera_voice(
    image: UploadFile = File(...),
    query: str = Form(default=""),  # Text query from speech recognition
    audio: Optional[UploadFile] = File(None),  # Optional audio file
    mode: str = Form(default="stepbystep")  # Mode selection
):
    """
    Enhanced endpoint for live camera assistance with voice input
    Handles image + voice transcription + optional audio file
    """
    try:
        print(f"Live assistance request - Image: {image.filename}, Query: {query}, Mode: {mode}")
        print(f"Audio file present: {audio.filename if audio else 'None'}")
        
        # Validate image
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read image content
        image_content = await image.read()
        
        # Store image in MongoDB GridFS
        image_file_id = db.fs.put(
            image_content,
            filename=image.filename,
            content_type=image.content_type
        )
        
        # Initialize variables for audio processing
        audio_file_id = None
        transcribed_audio_text = ""
        
        # Process audio if provided
        if audio:
            try:
                audio_content = await audio.read()
                
                # Store audio in MongoDB GridFS
                audio_file_id = db.fs.put(
                    audio_content,
                    filename=audio.filename,
                    content_type=audio.content_type
                )
                
                # Convert audio to text
                transcribed_audio_text = await convert_audio_to_text(audio_content, audio.content_type)
                print(f"Audio transcription: {transcribed_audio_text}")
                
            except Exception as audio_error:
                print(f"Audio processing error: {audio_error}")
                transcribed_audio_text = "Audio processing failed"
        
        # Combine all text inputs
        combined_query = ""
        if query.strip():
            combined_query += f"Voice input (real-time): {query.strip()}"
        
        if transcribed_audio_text and transcribed_audio_text not in ["Could not understand the audio clearly", "Audio processing temporarily unavailable", "Failed to process audio input", "Audio processing failed"]:
            if combined_query:
                combined_query += f"\nAdditional audio input: {transcribed_audio_text}"
            else:
                combined_query = f"Audio input: {transcribed_audio_text}"
        
        # Store the live assistance session in MongoDB
        session_metadata = {
            "image_grid_fs_id": str(image_file_id),
            "audio_grid_fs_id": str(audio_file_id) if audio_file_id else None,
            "image_filename": image.filename,
            "audio_filename": audio.filename if audio else None,
            "real_time_query": query,
            "transcribed_audio": transcribed_audio_text,
            "combined_query": combined_query,
            "mode": mode,
            "session_type": "live_camera_voice",
            "timestamp": datetime.now()
        }
        
        db.live_sessions_collection.insert_one(session_metadata)
        
        # Create enhanced prompt for live assistance - emphasize natural speech-friendly explanations
        base_prompt = """You are providing LIVE TUTORING assistance. The student is pointing their camera at a problem and speaking to you in real-time. 

Analyze the image carefully and respond to their voice input naturally, as if you're sitting right next to them helping with their homework.

Key guidelines:
1. Be conversational and encouraging
2. Reference what you see in the image specifically
3. Address their spoken question directly
4. Provide clear, step-by-step guidance appropriate to their learning level
5. Use proper academic notation when needed, but keep mathematical expressions SPEECH-FRIENDLY
6. Be patient and supportive like a good tutor would be

IMPORTANT FORMATTING RULES FOR MATHEMATICAL EXPRESSIONS:
- Use Unicode mathematical symbols when appropriate: θ, π, α, β, √, ∫, ∑, ≤, ≥, ≠, ≈, ±, ×, ÷
- For powers: prefer x² over x^2 for common squares, but x^2 is acceptable
- For fractions: write as "a/b" or use Unicode fractions like ½, ¾
- For subscripts: H₂O, CO₂, etc.
- NO LaTeX notation ($, \\frac, \\sin, \\theta, etc.)
- NO HTML tags or special markup
- When explaining steps verbally, use natural language: "x squared" rather than complex notation

Examples of GOOD mathematical explanations:
- "To solve x² + 5x = 0, we factor out x to get x(x + 5) = 0"
- "The derivative of 3x² is 6x"
- "For the quadratic formula: x = (-b ± √(b² - 4ac)) / 2a"
- "The area of a circle is π times r squared, or πr²"
"""
        
        if combined_query:
            prompt = f"""{base_prompt}
            
The student is showing you this image and has said: "{combined_query}"

Please help them understand and solve this problem step by step. Make your explanation clear and natural for voice synthesis."""
        else:
            prompt = f"""{base_prompt}
            
The student is showing you this image. They may have spoken but the audio wasn't clear. Please analyze the image and provide helpful guidance for whatever problem or question they're showing you. Make your explanation clear and natural for voice synthesis."""

        # Determine subject from context
        subject_hint = "general"
        query_lower = combined_query.lower()
        if any(term in query_lower for term in ["math", "equation", "calculate", "solve", "algebra", "geometry", "calculus"]):
            subject_hint = "math"
        elif any(term in query_lower for term in ["physics", "force", "motion", "energy", "velocity"]):
            subject_hint = "physics"
        elif any(term in query_lower for term in ["chemistry", "reaction", "molecule", "compound", "element"]):
            subject_hint = "chemistry"
        elif any(term in query_lower for term in ["biology", "cell", "organism", "gene", "evolution"]):
            subject_hint = "biology"

        # Generate solution using Gemini with enhanced context
        raw_solution = await generate_solution(prompt, image_content, image.content_type, subject_hint, mode)
        
        # Create dual response versions
        solution_versions = create_dual_response(raw_solution, mode)
        
        # Enhance the response for live interaction
        if mode == "stepbystep":
            display_solution = solution_versions["display"]
            speech_solution = solution_versions["speech"]
        else:
            display_solution = f"Let me help you with this problem. {solution_versions['display']}"
            speech_solution = f"Let me help you with this problem. {solution_versions['speech']}"
        
        return {
            "solution": display_solution,          # For visual display
            "speech_solution": speech_solution,    # For text-to-speech
            "transcribed_query": combined_query,
            "audio_transcription": transcribed_audio_text,
            "session_id": str(session_metadata.get("_id", "unknown"))
        }
        
    except Exception as e:
        print(f"Error in live camera voice assistance: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Live assistance failed: {str(e)}")
    
# This can be used for testing the API without a file upload
@router.post("/test-query")
async def test_query(
    query: str = Form(...),
    mode: str = Form(default="stepbystep")  # Add mode parameter with default value
):
    solution = await generate_solution(query, mode=mode)
    return {"solution": solution}
