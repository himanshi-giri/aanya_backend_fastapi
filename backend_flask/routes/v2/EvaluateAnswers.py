from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel
import os
import uuid
import cv2
import numpy as np
import easyocr  # Replaced pytesseract with easyocr
from PIL import Image
import re
import json
import aiohttp
import time
import logging
from dotenv import load_dotenv
import base64  # Added for image encoding

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Models for request/response
class TextEvaluationRequest(BaseModel):
    question: str
    totalMarks: int
    studentAnswer: str  # Added student answer field
    subject: Optional[str] = "mathematics"  # Default subject is mathematics
    grade: Optional[int] = 10  # Default grade is 10

class EvaluationResponse(BaseModel):
    feedback: str
    score: float
    detailed_analysis: Optional[Dict] = None
    
router = APIRouter()

# Temporary storage for uploaded files
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize EasyOCR reader - only do this once as it loads models
reader = None

def get_ocr_reader():
    """Initialize and return EasyOCR reader (lazy loading)"""
    global reader
    if reader is None:
        try:
            logger.info("Initializing EasyOCR reader...")
            reader = easyocr.Reader(['en'])  # Initialize for English
            logger.info("EasyOCR reader initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            return None
    return reader

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Get API key from environment variables
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# Function to call Gemini API
async def call_gemini_api(prompt, image_content=None, api_key=GEMINI_API_KEY):
    """Call Google Gemini 1.5 Flash API with given prompt and optional image."""
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in environment variables")
        raise HTTPException(status_code=500, detail="API key not configured")
    
    url = f"{GEMINI_API_URL}?key={api_key}"
    
    # Basic payload structure
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.95,
            "topK": 40,
            "maxOutputTokens": 8192
        }
    }
    
    # Add image to payload if provided
    if image_content:
        try:
            # Convert image to base64
            base64_image = base64.b64encode(image_content).decode('utf-8')
            # Add image as a part in the prompt
            payload["contents"][0]["parts"].insert(0, {
                "inline_data": {
                    "mime_type": "image/jpeg",  # Assuming JPEG, adjust if needed
                    "data": base64_image
                }
            })
            logger.info("Added image to Gemini API request")
        except Exception as e:
            logger.error(f"Error adding image to payload: {e}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Gemini API error: {error_text}")
                    return {
                        "error": f"API call failed with status {response.status}",
                        "details": error_text
                    }
                
                result = await response.json()
                
                # Check if we got a proper response
                if "candidates" in result and len(result["candidates"]) > 0:
                    text_content = result["candidates"][0]["content"]["parts"][0]["text"]
                    return {"text": text_content}
                else:
                    logger.error(f"Unexpected API response structure: {result}")
                    return {"error": "Invalid response format from Gemini API"}
    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        return {"error": f"API call exception: {str(e)}"}

# Helper functions
def extract_text_from_image(image_path):
    """Extract text from an image using EasyOCR."""
    try:
        # Get OCR reader
        reader = get_ocr_reader()
        if reader is None:
            logger.error("EasyOCR reader not available")
            return "Error: OCR service unavailable"
        
        # Read the image
        img = cv2.imread(image_path)
        
        # Preprocess the image for better OCR results
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Apply adaptive thresholding
        adaptive_thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Run OCR
        results = reader.readtext(adaptive_thresh)
        
        # Extract and combine text
        text = ""
        for (bbox, content, prob) in results:
            # Only include text with reasonable confidence
            if prob > 0.5:  # Confidence threshold
                text += content + " "
        
        # Handle mathematical symbols more effectively
        # Replace common OCR errors for math symbols
        text = text.replace("x", "×").replace("X", "×")
        text = re.sub(r'(\d)-(\d)', r'\1−\2', text)  # Convert hyphens between numbers to minus signs
        
        return text.strip()
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return f"Error extracting text from image: {str(e)}"

# New function to extract text directly from image bytes
def extract_text_from_image_bytes(image_bytes):
    """Extract text from image bytes using EasyOCR."""
    try:
        # Get OCR reader
        reader = get_ocr_reader()
        if reader is None:
            logger.error("EasyOCR reader not available")
            return "Error: OCR service unavailable"
        
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Preprocess the image for better OCR results
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Apply adaptive thresholding
        adaptive_thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Run OCR
        results = reader.readtext(adaptive_thresh)
        
        # Extract and combine text
        text = ""
        for (bbox, content, prob) in results:
            # Only include text with reasonable confidence
            if prob > 0.5:  # Confidence threshold
                text += content + " "
        
        # Handle mathematical symbols more effectively
        text = text.replace("x", "×").replace("X", "×")
        text = re.sub(r'(\d)-(\d)', r'\1−\2', text)  # Convert hyphens between numbers to minus signs
        
        return text.strip()
    except Exception as e:
        logger.error(f"OCR error on image bytes: {e}")
        return f"Error extracting text from image: {str(e)}"

def format_evaluation_prompt(question, student_answer, subject, grade, total_marks):
    """Create a detailed prompt for Gemini to evaluate student solutions with thorough, teacher-like feedback."""
    
    prompt = f"""
You are an expert educational evaluator for K-12 students. Your role is to carefully analyze solutions and provide constructive, detailed feedback that helps students learn and improve.

QUESTION:
{question}

STUDENT'S ANSWER:
{student_answer}

TOTAL MARKS: {total_marks}
SUBJECT: {subject}
GRADE LEVEL: {grade}

When evaluating this solution:

1. Begin with a short summary acknowledging the student's strengths - what concepts they understood correctly and applied well.

2. Perform a detailed step-by-step analysis of the solution:
   - Identify each logical step in the student's work
   - For each step, analyze its mathematical/scientific correctness 
   - Point out where precise reasoning was demonstrated
   - Identify any conceptual errors or procedural mistakes

3. For any errors found:
   - Clearly explain what the specific mistake is
   - Why it's mathematically/scientifically incorrect 
   - Show the correct approach with explicit calculations
   - Connect the correction to fundamental principles

4. Look for areas of improvement even in correct solutions:
   - More efficient solution methods
   - Better organization or presentation
   - Opportunities for deeper mathematical/scientific insight
   - Alternative approaches worth considering

5. Score the solution fairly based on:
   - Correctness of key steps
   - Proper application of concepts
   - Completeness of the solution
   - Mathematical/scientific reasoning demonstrated

6. Provide specific, actionable recommendations that will help the student:
   - Strengthen conceptual understanding
   - Improve problem-solving techniques
   - Develop better solution presentation skills
   - Gain deeper insights into the subject matter

You MUST format your response as a valid JSON object with the following structure:

{{
  "score": (numerical score as float between 0 and {total_marks}),
  "feedback": "Brief summary of evaluation addressing the student directly with key strengths and areas for improvement",
  "detailed_analysis": {{
    "problem_understanding": "Analysis of how well the student understood the problem's requirements and constraints",
    "approach_evaluation": "Assessment of the student's problem-solving strategy and methodology",
    "step_by_step_analysis": [
      {{
        "step_number": 1,
        "step_description": "Description of this step in the solution",
        "student_work": "What the student did in this step",
        "correctness": "Correct/Partially Correct/Incorrect",
        "explanation": "Detailed explanation of what's right or wrong, with specific mathematical reasoning",
        "correction": "The correct approach for this step with explicit calculations if needed"
      }},
      // Additional steps as needed
    ],
    "conceptual_understanding": "Evaluation of the student's grasp of the underlying principles and concepts",
    "scoring_breakdown": [
      {{
        "component": "Name of scored component (e.g., 'Correct application of the quadratic formula')",
        "marks_awarded": X,
        "marks_possible": Y,
        "justification": "Specific reason for these marks with mathematical details"
      }},
      // Additional scoring components
    ],
    "correct_solution": "Complete step-by-step solution showing the optimal approach with all calculations",
    "improvement_suggestions": [
      "Specific, actionable suggestion 1",
      "Specific, actionable suggestion 2",
      // Additional suggestions
    ]
  }}
}}

IMPORTANT GUIDELINES:

1. Address the student directly using "you" and "your" rather than referring to "the student"
2. Maintain an encouraging, supportive tone while being honest about errors
3. Be specific about mathematical/scientific concepts and calculations in your feedback
4. Break down complex solutions into clear, logical steps
5. Ensure your evaluation is appropriate for the student's grade level ({grade})
6. Focus on conceptual understanding rather than just procedural correctness
7. Provide detailed reasoning for point deductions and awards
8. Highlight both strengths and areas for improvement
9. Include complete mathematical calculations in your corrections
10. Your JSON response MUST be valid - no markdown, no code blocks, properly escaped characters

Remember that your goal is to help the student learn from this assessment, not just assign a score.
"""
    return prompt
async def evaluate_with_gemini(question, student_answer, subject, grade, total_marks, image_content=None):
    """Use Gemini API to evaluate the  answer, with optional image analysis."""
    prompt = format_evaluation_prompt(question, student_answer, subject, grade, total_marks)
    
    # Call Gemini API, passing image content if available
    response = await call_gemini_api(prompt, image_content)
    
    if "error" in response:
        logger.error(f"Gemini API error: {response['error']}")
        # Fallback to basic evaluation
        return {
            "feedback": f"⚠️ **System is experiencing issues.** We're unable to provide detailed feedback at the moment.\n\nYour answer has been recorded and will be evaluated later.",
            "score": round(total_marks * 0.5, 1),  # Default to 50% as fallback
            "detailed_analysis": {
                "strengths": ["Unable to analyze strengths"],
                "weaknesses": ["Unable to analyze weaknesses"],
                "misconceptions": [],
                "corrections": [],
                "improvement_tips": ["Please try submitting again later"]
            }
        }
    
    try:
        # Clean the response text - remove markdown code blocks if present
        text = response["text"]
        # Check if response is wrapped in markdown code blocks
        if text.startswith("```json") or text.startswith("```"):
            # Extract the JSON content from between code blocks
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
            if match:
                text = match.group(1)
        
        # Parse the JSON response
        evaluation_data = json.loads(text)
        
        # Ensure score is within bounds
        evaluation_data["score"] = max(0, min(float(evaluation_data["score"]), total_marks))
        return evaluation_data

    
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error from Gemini response: {e}")
        logger.error(f"Raw response: {response['text']}")
        
        try:
            # Try to extract the JSON using a more robust method
            text = response["text"]
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    extracted_json = json_match.group(0)
                    evaluation_data = json.loads(extracted_json)
                    evaluation_data["score"] = max(0, min(float(evaluation_data["score"]), total_marks))
                    return evaluation_data
                except:
                    pass
        except:
            pass
            
        # If all else fails, try to extract score using regex as fallback
        score_match = re.search(r'score"?\s*:\s*(\d+\.?\d*)', response["text"])
        score = float(score_match.group(1)) if score_match else total_marks * 0.5
        score = max(0, min(score, total_marks))
        
        # Return a formatted response as fallback
        return {
            "feedback": f"⚠️ **Partial evaluation:** We encountered an issue processing the detailed feedback.\n\nBased on your answer, you've earned approximately {score}/{total_marks} marks.",
            "score": score,
            "detailed_analysis": {
                "strengths": ["Analysis incomplete"],
                "weaknesses": ["Analysis incomplete"],
                "misconceptions": [],
                "corrections": [],
                "improvement_tips": ["Please ensure your answer is clear and complete"]
            }
        }

# API endpoints
@router.post("/evaluate-text")
async def evaluate_text_endpoint(request: dict = Body(...)):
    """Evaluate a problem from text input using Gemini API."""
    try:
        # Log incoming request for debugging
        logger.info(f"Received evaluation request: {request}")
        
        # Extract and validate required fields
        question = request.get("question", "")
        student_answer = request.get("studentAnswer", "")
        total_marks = request.get("totalMarks", 1)
        subject = request.get("subject", "mathematics")
        grade = request.get("grade", 10)
        
        # Validate input
        if not student_answer:
            logger.warning("Missing student answer in request")
            return JSONResponse(
                status_code=400,
                content={"detail": "Student answer is required for evaluation", "feedback": "No answer provided", "score": 0}
            )
        
        # Log extracted parameters
        logger.info(f"Processing with: question='{question}', answer='{student_answer}', marks={total_marks}")
        
        # Evaluate using Gemini
        evaluation = await evaluate_with_gemini(
            question=question,
            student_answer=student_answer,
            subject=subject,
            grade=grade,
            total_marks=total_marks
        )
        return evaluation
    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        # Return a more helpful error response
        return JSONResponse(
            status_code=500,
            content={"detail": f"Evaluation error: {str(e)}", "feedback": "System error occurred", "score": 0}
        )

# Enhanced evaluate with image endpoint
@router.post("/evaluate/with-image", response_model=EvaluationResponse)
async def evaluate_with_image(
    question: str = Form(...),
    totalMarks: int = Form(...),
    studentAnswer: Optional[str] = Form(""),
    subject: str = Form("mathematics"),
    grade: int = Form(10),
    answerImage: Optional[UploadFile] = File(None),
    questionImage: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None)  # Generic file field for compatibility
):
    """Evaluate a problem using text and/or images using Gemini API."""
    try:
        # Log request information for debugging
        logger.info(f"Image evaluation request: question='{question}', marks={totalMarks}")
        if questionImage:
            logger.info(f"Question image provided: {questionImage.filename}")
        if answerImage:
            logger.info(f"Answer image provided: {answerImage.filename}")
        if file:
            logger.info(f"Generic file provided: {file.filename}")
            # Treat 'file' as answerImage if it's an image, otherwise ignore
            if file.filename and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                answerImage = file
        
        combined_question = question
        combined_answer = studentAnswer
        
        # Variables to hold raw image content for Gemini
        question_image_content = None
        answer_image_content = None
        
        # Process question image if provided
        if questionImage:
            # Save the image temporarily and keep content for Gemini
            content = await questionImage.read()
            question_image_content = content
            
            # Extract text from image for combination with text input
            temp_image_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{os.path.splitext(questionImage.filename)[1]}")
            with open(temp_image_path, "wb") as buffer:
                buffer.write(content)
            
            # Extract text from image
            image_text = extract_text_from_image(temp_image_path)
            combined_question += f"\n{image_text}"
            
            # Clean up
            os.remove(temp_image_path)
        
        # Process answer image if provided
        if answerImage:
            # Save the image temporarily and keep content for Gemini
            content = await answerImage.read()
            answer_image_content = content
            
            # Extract text from image for combination with text input
            temp_image_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{os.path.splitext(answerImage.filename)[1]}")
            with open(temp_image_path, "wb") as buffer:
                buffer.write(content)
            
            # Extract text from image
            image_text = extract_text_from_image(temp_image_path)
            combined_answer += f"\n{image_text}"
            
            # Clean up
            os.remove(temp_image_path)
        
        # If no answer is provided but we have an answer image, use the extracted text
        if not combined_answer.strip() and answer_image_content:
            logger.info("Using extracted text from answer image as no text answer was provided")
            combined_answer = extract_text_from_image_bytes(answer_image_content)
        
        # Validate combined input
        if not combined_answer.strip() and not answer_image_content:
            logger.warning("No answer provided in request")
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "No student answer provided in text or image",
                    "feedback": "No answer to evaluate was provided.",
                    "score": 0
                }
            )
        
        # Choose which image to send to Gemini (prioritize answer image)
        image_for_gemini = answer_image_content if answer_image_content else question_image_content
        
        # Evaluate using Gemini
        evaluation = await evaluate_with_gemini(
            question=combined_question,
            student_answer=combined_answer,
            subject=subject,
            grade=grade,
            total_marks=totalMarks,
            image_content=image_for_gemini
        )
        return evaluation
    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Evaluation error: {str(e)}",
                "feedback": "An error occurred while processing your submission.",
                "score": 0
            }
        )

# New endpoint for direct image evaluation without text
@router.post("/evaluate/image-answer", response_model=EvaluationResponse)
async def evaluate_image_answer(
    question: str = Form(...),
    totalMarks: int = Form(...),
    subject: str = Form("mathematics"),
    grade: int = Form(10),
    image: UploadFile = File(...)
):
    """Evaluate a student answer provided as an image."""
    try:
        # Log incoming request
        logger.info(f"Received image evaluation request for question: {question}")
        
        # Read image content
        image_content = await image.read()
        
        # Extract text from image
        extracted_text = extract_text_from_image_bytes(image_content)
        logger.info(f"Extracted text from image: {extracted_text[:100]}...")
        
        # Evaluate using both the extracted text and the image itself
        evaluation = await evaluate_with_gemini(
            question=question,
            student_answer=extracted_text,
            subject=subject,
            grade=grade,
            total_marks=totalMarks,
            image_content=image_content  # Pass the raw image to Gemini
        )
        
        return evaluation
    except Exception as e:
        logger.error(f"Image evaluation error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Image evaluation error: {str(e)}",
                "feedback": "An error occurred while processing your image submission.",
                "score": 0
            }
        )

# Subject-specific evaluation endpoints
@router.post("/evaluate/subject/{subject}", response_model=EvaluationResponse)
async def evaluate_by_subject(
    subject: str,
    request: TextEvaluationRequest
):
    """
    Evaluate a problem for a specific subject area.
    Subjects can be: mathematics, physics, chemistry, biology, etc.
    """
    try:
        # Set the subject from the path parameter
        request.subject = subject
        
        # Validate input
        if not request.studentAnswer:
            return JSONResponse(
                status_code=400,
                content={"detail": "Student answer is required for evaluation"}
            )
        
        # Evaluate using Gemini
        evaluation = await evaluate_with_gemini(
            question=request.question,
            student_answer=request.studentAnswer,
            subject=subject,
            grade=request.grade,
            total_marks=request.totalMarks
        )
        
        return evaluation
    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Evaluation error: {str(e)}")

# New endpoint to handle combined image evaluation with subject specification
@router.post("/evaluate/subject/{subject}/with-image", response_model=EvaluationResponse)
async def evaluate_subject_with_image(
    subject: str,
    question: str = Form(...),
    totalMarks: int = Form(...),
    studentAnswer: Optional[str] = Form(""),
    grade: int = Form(10),
    answerImage: Optional[UploadFile] = File(None)
):
    """Evaluate a subject-specific problem with image support."""
    try:
        # Log request
        logger.info(f"Subject-specific image evaluation for {subject}: question='{question}'")
        
        combined_answer = studentAnswer
        answer_image_content = None
        
        # Process answer image if provided
        if answerImage:
            # Read image content
            answer_image_content = await answerImage.read()
            
            # Extract text from image
            extracted_text = extract_text_from_image_bytes(answer_image_content)
            combined_answer += f"\n{extracted_text}"
        
        # Validate input
        if not combined_answer.strip() and not answer_image_content:
            return JSONResponse(
                status_code=400,
                content={"detail": "Student answer is required (text or image)"}
            )
        
        # Evaluate using Gemini
        evaluation = await evaluate_with_gemini(
            question=question,
            student_answer=combined_answer,
            subject=subject,
            grade=grade,
            total_marks=totalMarks,
            image_content=answer_image_content
        )
        
        return evaluation
    except Exception as e:
        logger.error(f"Subject evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Subject evaluation error: {str(e)}")

# Add health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint to verify the service is running."""
    try:
        # Check if OCR is available
        ocr_status = "available" if get_ocr_reader() is not None else "unavailable"
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "ocr_status": ocr_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(e)}
        )