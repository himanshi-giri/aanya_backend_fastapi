from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from pydantic import BaseModel
import os
import fitz
import google.generativeai as genai
from datetime import datetime
import base64
from typing import Optional,List , Dict
import random
import speech_recognition as sr
import io
import tempfile
from pydub import AudioSegment
import re
from fastapi.responses import JSONResponse
import json
from database.db import db , fs


router = APIRouter(prefix="/doubt", tags=["Doubt Solver"])

# Load environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Enhanced Pydantic models
class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[int] = None
    hasImage: Optional[bool] = False
    imageName: Optional[str] = None
    imageContext: Optional[str] = None
    hasFile: Optional[bool] = False
    fileName: Optional[str] = None
    fileType: Optional[str] = None
    fileContext: Optional[str] = None
    hasVoice: Optional[bool] = False
    voiceContext: Optional[str] = None
    hasLiveCamera: Optional[bool] = False
    liveCameraContext: Optional[str] = None

class ConversationSummary(BaseModel):
    subjects: List[str] = []
    topics: List[str] = []
    messageCount: int = 0

class ChatContext(BaseModel):
    conversationSummary: Optional[ConversationSummary] = None
    recentHistory: List[ChatMessage] = []
    totalMessages: int = 0

class TextRequest(BaseModel):
    text: str
    mode: Optional[str] = "stepbystep"  
    chat_history: Optional[List[str]] = []  # Deprecated - keeping for backward compatibility
    chatHistory: Optional[ChatContext] = None  # New structured chat history
    currentSubject: Optional[str] = "general"

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
# Enhanced helper function to format chat history for context
def format_chat_history_for_context(chat_context: ChatContext, current_subject: str = "general") -> str:
    """
    Format chat history into a contextual string for the AI model
    """
    if not chat_context or not chat_context.recentHistory:
        return ""
    
    context_parts = []
    
    # Add conversation summary if available
    if chat_context.conversationSummary and chat_context.conversationSummary.messageCount > 0:
        summary = chat_context.conversationSummary
        context_parts.append(f"Previous conversation covered {', '.join(summary.subjects)} topics")
        if summary.topics:
            context_parts.append(f"Key topics discussed: {', '.join(summary.topics[:5])}")
    
    # Add recent conversation history
    if chat_context.recentHistory:
        context_parts.append("Recent conversation:")
        
        for msg in chat_context.recentHistory[-10:]:  # Last 10 messages for context
            role_prefix = "Student:" if msg.role == "user" else "Tutor:"
            
            # Add context about multimedia inputs
            media_context = []
            if msg.hasImage:
                media_context.append(f"[with image: {msg.imageName or 'uploaded image'}]")
            if msg.hasFile:
                media_context.append(f"[with file: {msg.fileName or 'uploaded document'}]")
            if msg.hasVoice:
                media_context.append("[with voice input]")
            if msg.hasLiveCamera:
                media_context.append("[with live camera assistance]")
            
            media_str = " ".join(media_context)
            message_text = f"{role_prefix} {msg.content} {media_str}".strip()
            context_parts.append(message_text)
    
    # Add current subject context
    if current_subject and current_subject != "general":
        context_parts.append(f"Current focus area: {current_subject}")
    
    return "\n".join(context_parts)

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
async def generate_solution(prompt, file_content=None, file_type=None, subject_hint="general", mode="stepbystep",chat_context=None, current_subject="general"):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare content parts based on what's available
        content_parts = [prompt]
         # Add chat history context if available
        context_string = ""
        if chat_context:
            context_string = format_chat_history_for_context(chat_context, current_subject)
        
        # Create contextual prompt
        if context_string:
            contextual_prompt = f"""CONVERSATION CONTEXT:
{context_string}

CURRENT QUESTION:
{prompt}

Please provide a response that takes into account the conversation history and builds upon previous explanations when relevant. If this question relates to something we discussed earlier, reference that context appropriately."""
        else:
            contextual_prompt = prompt
        
        content_parts.append(contextual_prompt)
        
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
        
         # Determine the subject based on the prompt content and context
        if subject_hint != "general":
            subject = subject_hint
        elif current_subject != "general":
            subject = current_subject
        elif "math" in prompt.lower() or "calculate" in prompt.lower() or "equation" in prompt.lower() or "integral" in prompt.lower():
            subject = "math"
        elif "physics" in prompt.lower() or "force" in prompt.lower() or "motion" in prompt.lower() or "energy" in prompt.lower():
            subject = "physics"
        elif "chemistry" in prompt.lower() or "reaction" in prompt.lower() or "molecule" in prompt.lower() or "compound" in prompt.lower():
            subject = "chemistry"
        elif "biology" in prompt.lower() or "cell" in prompt.lower() or "organism" in prompt.lower() or "gene" in prompt.lower():
            subject = "biology"
        else:
            subject = "general"
            
        # Select a random follow-up question from the appropriate category
        follow_up = random.choice(follow_up_questions[subject])
        
        # Create an enhanced prompt based on the selected mode
        if mode == "stepbystep":
            # Step by Step Doubt Clearing mode
            enhanced_prompt = f"""{contextual_prompt}
You are a Tutor for K-12 students. You are patient and always eager to help students learn. Students come to you when they get stuck with a problem.

IMPORTANT: If the student's question contains phrases like "final answer", "complete solution", "full solution", "show me the answer", "what's the answer", or "give me the answer", provide a complete solution with all steps clearly explained:
1. Break down the problem into clear steps
2. Show all calculations and reasoning
3. Provide the final answer
4. Explain why this is the correct answer

Otherwise, follow these guidelines:
1. DO NOT reveal the complete solution to any problem
2. Break the problem into small steps and guide the student through ONLY THE NEXT STEP
3. Present ONLY ONE step (the next logical step) and ask the student a leading question
4. Give just enough information to help the student figure out this step on their own
5. Offer a hint if needed, but don't solve it for them
6. Your response should be focused only on the immediate next step the student should take

Encourage the student to think critically and work through the problems on their own.
Your role is to facilitate learning, not provide answers.

You possess deep and accurate knowledge of Math, Physics, Chemistry, Biology, and Social Science as taught under CBSE and ICSE boards. 
You also have expert-level knowledge of the syllabus required for competitive exams like IIT-JEE and NEET.

End with a question like: "Would you like me to explain any part of the solution in more detail?" or "{follow_up}"
"""
        else:
            # Homework Help mode (complete solution)
            enhanced_prompt = f"""{contextual_prompt}
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
            "original_prompt": contextual_prompt,
            "solution": response.text,
            "timestamp": datetime.now(),
            "subject": subject,
            "mode": mode,
            "has_chat_context": bool(chat_context and chat_context.recentHistory),
            "context_length": len(chat_context.recentHistory) if chat_context and chat_context.recentHistory else 0,
            "current_subject": current_subject
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
         # Handle both old and new chat history formats
        chat_context = None
        if request.chatHistory:
            chat_context = request.chatHistory
        elif request.chat_history:
            # Convert old format to new format for backward compatibility
            formatted_history = []
            for i, chat in enumerate(request.chat_history):
                role = "user" if i % 2 == 0 else "assistant"
                formatted_history.append(ChatMessage(role=role, content=chat))
            chat_context = ChatContext(recentHistory=formatted_history)
        
        prompt = f"""
You are a helpful and knowledgeable AI tutor. Use the following conversation history to understand the user's context.
Question: {request.text}

Respond clearly using correct academic notation. Avoid HTML tags.
"""
        # Pass the mode to generate_solution
        solution = await generate_solution(prompt, mode=request.mode, chat_context=chat_context, current_subject=request.currentSubject or "general")
        return SolutionResponse(solution=solution)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# Helper function to parse chat history from form data
def parse_chat_history_from_form(chat_history_str: str) -> Optional[ChatContext]:
    """
    Parse chat history JSON string from form data
    """
    try:
        if not chat_history_str:
            return None
        
        chat_data = json.loads(chat_history_str)
        
        # Handle the nested structure from frontend
        if isinstance(chat_data, dict):
            recent_history = []
            if "recentHistory" in chat_data:
                for msg in chat_data["recentHistory"]:
                    recent_history.append(ChatMessage(**msg))
            
            conversation_summary = None
            if "conversationSummary" in chat_data and chat_data["conversationSummary"]:
                conversation_summary = ConversationSummary(**chat_data["conversationSummary"])
            
            return ChatContext(
                recentHistory=recent_history,
                conversationSummary=conversation_summary,
                totalMessages=chat_data.get("totalMessages", len(recent_history))
            )
        
        return None
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        print(f"Error parsing chat history: {e}")
        return None


@router.post("/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    mode: str = Form(default="stepbystep"), # Add mode parameter with default value
    chatHistory: str = Form(default=""),  # JSON string of chat history
    currentSubject: str = Form(default="general"),
    query: str = Form(default="")  # Additional query text
):
    try:
        # Read file content
        content = await file.read()
        # Parse chat history
        chat_context = parse_chat_history_from_form(chatHistory)
        
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
            "current_subject": currentSubject,
            "has_chat_context": bool(chat_context and chat_context.recentHistory),
            "additional_query": query,
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
        solution = await generate_solution(prompt, content, file.content_type, mode=mode, chat_context=chat_context, current_subject=currentSubject)
        
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
    mode: str = Form(default="stepbystep"),  # Add mode parameter with default value
    chatHistory: str = Form(default=""),  # JSON string of chat history
    currentSubject: str = Form(default="general"),
    query: str = Form(default="")  # Additional query text
):
    try:
        # Check if the file is actually an image
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image content
        image_content = await image.read()
         # Parse chat history
        chat_context = parse_chat_history_from_form(chatHistory)
        
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
            "current_subject": currentSubject,
            "has_chat_context": bool(chat_context and chat_context.recentHistory),
            "additional_query": query,
            "timestamp": datetime.now()
        }
        
        db.uploads_collection.insert_one(image_metadata)
        
        # Generate solution based on image and mode
        prompt = "Please analyze the provided image and explain the solution in a clear manner. Start by identifying what is given and what needs to be found. Then outline the method or concept used to solve it. Use correct academic notation and terminology (e.g., x², ∫, Δt, moles, sin(θ), etc.), and avoid unnecessary special characters or HTML tags."
        solution = await generate_solution(prompt, image_content, image.content_type, "math", mode=mode, chat_context=chat_context, current_subject=currentSubject)
        return {"solution": solution}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-voice")
async def send_voice(
    voice: UploadFile = File(...),
    mode: str = Form(default="stepbystep"),  # Add mode parameter with default value
    chatHistory: str = Form(default=""),  # JSON string of chat history
    currentSubject: str = Form(default="general")
):
    try:
        # Read voice content
        voice_content = await voice.read()
        # Parse chat history
        chat_context = parse_chat_history_from_form(chatHistory)
        
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
            "current_subject": currentSubject,
            "has_chat_context": bool(chat_context and chat_context.recentHistory),
            "timestamp": datetime.now()
        }
        
        db.uploads_collection.insert_one(voice_metadata)
        
        # Convert voice to text
        transcribed_text = await convert_audio_to_text(voice_content, voice.content_type)
        
        # Generate solution based on transcribed text and mode
        if transcribed_text and transcribed_text not in ["Could not understand the audio clearly", "Audio processing temporarily unavailable", "Failed to process audio input"]:
            prompt = f"The user asked via voice: {transcribed_text}"
            solution = await generate_solution(prompt, mode=mode , chat_context=chat_context, current_subject=currentSubject)
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
    mode: str = Form(default="stepbystep"),  # Add mode parameter with default value
    chatHistory: str = Form(default=""),  # JSON string of chat history
    currentSubject: str = Form(default="general")

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
         # Parse chat history
        chat_context = parse_chat_history_from_form(chatHistory)
        
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
            "current_subject": currentSubject,
            "has_chat_context": bool(chat_context and chat_context.recentHistory),
            "context_length": len(chat_context.recentHistory) if chat_context and chat_context.recentHistory else 0,
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
        subject_hint = currentSubject if currentSubject != "general" else "math"  # Default for mathematical images
        if "chemistry" in query.lower() or "molecule" in query.lower() or "reaction" in query.lower():
            subject_hint = "chemistry"
        elif "physics" in query.lower() or "force" in query.lower() or "motion" in query.lower():
            subject_hint = "physics"
        elif "biology" in query.lower() or "cell" in query.lower() or "organism" in query.lower():
            subject_hint = "biology"
       

        # Generate answer from Gemini with image, text, and mode
        solution = await generate_solution(prompt, image_content, image.content_type, subject_hint, mode=mode, chat_context=chat_context, current_subject=currentSubject)

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
    mode: str = Form(default="stepbystep"),  # Mode selection
    chatHistory: str = Form(default=""),  # JSON string of chat history
    currentSubject: str = Form(default="general")  # Current subject context
):
    """
    Enhanced endpoint for live camera assistance with voice input
    Handles image + voice transcription + optional audio file
    """
    try:
        print(f"Live assistance request - Image: {image.filename}, Query: {query}, Mode: {mode}")
        print(f"Audio file present: {audio.filename if audio else 'None'}")
        print(f"Current subject: {currentSubject}")
        # Validate image
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read image content
        image_content = await image.read()
         # Parse chat history
        chat_context = parse_chat_history_from_form(chatHistory)
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
            "current_subject": currentSubject,
            "has_chat_context": bool(chat_context and chat_context.recentHistory),
            "context_length": len(chat_context.recentHistory) if chat_context and chat_context.recentHistory else 0,
            "session_type": "live_camera_voice",
            "timestamp": datetime.now()
        }
        
        db.live_sessions_collection.insert_one(session_metadata)
        
        # Create enhanced prompt for live assistance - emphasize natural speech-friendly explanations
        base_prompt = """You are providing LIVE TUTORING assistance. The student is pointing their camera at a problem and speaking to you in real-time. 

Analyze the image carefully and respond to their voice input naturally, as if you're sitting right next to them helping with their homework.
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
        raw_solution = await generate_solution(prompt, image_content, image.content_type, subject_hint, mode,chat_context=chat_context, current_subject=currentSubject)
        
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
            "session_id": str(session_metadata.get("_id", "unknown")),
            "chat_context_applied": bool(chat_context and chat_context.recentHistory),
            "context_length": len(chat_context.recentHistory) if chat_context and chat_context.recentHistory else 0
        }
        
    except Exception as e:
        print(f"Error in live camera voice assistance: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Live assistance failed: {str(e)}")
    
# This can be used for testing the API without a file upload
@router.post("/test-query")
async def test_query(
    query: str = Form(...),
    mode: str = Form(default="stepbystep"),  # Add mode parameter with default value
    chatHistory: str = Form(default=""),  # JSON string of chat history
    currentSubject: str = Form(default="general")  # Current subject context
):
    """
    Test endpoint with chat history support
    """
    try:
        # Parse chat history
        chat_context = parse_chat_history_from_form(chatHistory)
        
        solution = await generate_solution(
            query, 
            mode=mode, 
            chat_context=chat_context, 
            current_subject=currentSubject
        )
        
        return {
            "solution": solution,
            "chat_context_applied": bool(chat_context and chat_context.recentHistory),
            "context_length": len(chat_context.recentHistory) if chat_context and chat_context.recentHistory else 0
        }
    except Exception as e:
        print(f"Error in test query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Test query failed: {str(e)}")
