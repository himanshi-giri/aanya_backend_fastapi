from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel
import os
import uuid
import cv2
import numpy as np
import easyocr
from PIL import Image
import re
import json
import aiohttp
import time
import logging
from dotenv import load_dotenv
import base64
import markdown
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    hasScore: Optional[bool] = False
    score: Optional[float] = None
    totalMarks: Optional[int] = None
    evaluationContext: Optional[str] = None
class ConversationSummary(BaseModel):
    subjects: List[str] = []
    topics: List[str] = []
    messageCount: int = 0
    evaluationHistory: List[Dict[str, Any]] = []    

class ChatContext(BaseModel):
    recentHistory: List[ChatMessage] = []
    totalMessages: int = 0
    conversationSummary: Optional[ConversationSummary] = None   

# Models for request/response
class TextEvaluationRequest(BaseModel):
    question: str
    totalMarks: int
    studentAnswer: str
    subject: Optional[str] = "mathematics"
    grade: Optional[int] = 10
    chatHistory: Optional[Union[str, Dict, ChatContext]] = None
    currentSubject: Optional[str] = "general"
    hasVoiceInput: Optional[bool] = False

class EvaluationResponse(BaseModel):
    feedback: str
    score: float
    detailed_analysis: Optional[Dict] = None
    formatted_feedback: Optional[str] = None  # New field for beautifully formatted feedback
    contextual_insights: Optional[Dict] = None
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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# Enhanced chat history processing functions
def parse_chat_history(chat_history_data):
    """Parse and validate chat history from various formats."""
    if not chat_history_data:
        return None
    
    try:
        # Handle string JSON
        if isinstance(chat_history_data, str):
            chat_history_data = json.loads(chat_history_data)
        
        # Handle direct ChatContext object
        if isinstance(chat_history_data, dict):
            return ChatContext(**chat_history_data)
        
        return chat_history_data
    except Exception as e:
        logger.warning(f"Failed to parse chat history: {e}")
        return None

def analyze_conversation_context(chat_context: ChatContext):
    """Analyze conversation context to provide better evaluation insights."""
    if not chat_context or not chat_context.recentHistory:
        return {}
    
    analysis = {
        "conversation_length": chat_context.totalMessages,
        "recent_subjects": [],
        "learning_progression": [],
        "common_mistakes": [],
        "student_strengths": [],
        "interaction_patterns": {}
    }
    
    # Analyze recent messages
    for msg in chat_context.recentHistory[-10:]:  # Last 10 messages
        if msg.role == "user":
            # Detect subjects in user messages
            detected_subject = detect_subject_from_text(msg.content)
            if detected_subject not in analysis["recent_subjects"]:
                analysis["recent_subjects"].append(detected_subject)
             # Extract conversation topics
            topics = extract_conversation_topics(msg.content)
            analysis["conversation_topics"].extend(topics)
            
            # Detect mood indicators
            mood = detect_mood_indicators(msg.content)
            if mood:
                analysis["student_mood_indicators"].append(mood)
        elif msg.role == "assistant" and msg.hasScore:
            # Track learning progression from scores
            analysis["learning_progression"].append({
                "score": msg.score,
                "total_marks": msg.totalMarks,
                "percentage": (msg.score / msg.totalMarks) * 100 if msg.totalMarks > 0 else 0,
                "timestamp": msg.timestamp
            })
    
    # Analyze conversation summary if available
    if chat_context.conversationSummary:
        summary = chat_context.conversationSummary
        analysis["historical_subjects"] = summary.subjects
        analysis["discussion_topics"] = summary.topics
        analysis["total_evaluations"] = len(summary.evaluationHistory)
        
        # Calculate average performance
        if summary.evaluationHistory:
            scores = [eval_data.get("score", 0) for eval_data in summary.evaluationHistory]
            total_marks = [eval_data.get("totalMarks", 1) for eval_data in summary.evaluationHistory]
            percentages = [(s/t)*100 for s, t in zip(scores, total_marks) if t > 0]
            analysis["average_performance"] = sum(percentages) / len(percentages) if percentages else 0
    
    # Analyze interaction patterns
    analysis["interaction_patterns"] = {
        "uses_images": any(msg.hasImage for msg in chat_context.recentHistory),
        "uses_voice": any(msg.hasVoice for msg in chat_context.recentHistory),
        "uploads_files": any(msg.hasFile for msg in chat_context.recentHistory),
        "multi_modal_learner": sum([
            any(msg.hasImage for msg in chat_context.recentHistory),
            any(msg.hasVoice for msg in chat_context.recentHistory),
            any(msg.hasFile for msg in chat_context.recentHistory)
        ]) >= 2,
        "conversation_frequency": len(chat_context.recentHistory),
        "casual_conversation_ratio": calculate_casual_ratio(chat_context.recentHistory)
    }
    
    return analysis
def extract_conversation_topics(text):
    """Extract topics from conversation text."""
    text_lower = text.lower()
    topics = []
    
    # Academic topics
    if any(word in text_lower for word in ['homework', 'assignment', 'test', 'exam', 'quiz']):
        topics.append('academic_work')
    if any(word in text_lower for word in ['confused', 'don\'t understand', 'help', 'explain']):
        topics.append('seeking_help')
    if any(word in text_lower for word in ['good', 'great', 'awesome', 'cool', 'nice']):
        topics.append('positive_feedback')
    if any(word in text_lower for word in ['difficult', 'hard', 'challenging', 'struggle']):
        topics.append('difficulty_expression')
    
    return topics

def detect_mood_indicators(text):
    """Detect student's mood from their message."""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['excited', 'happy', 'great', 'awesome', 'love']):
        return 'positive'
    elif any(word in text_lower for word in ['confused', 'frustrated', 'difficult', 'hard', 'hate']):
        return 'struggling'
    elif any(word in text_lower for word in ['tired', 'boring', 'whatever', 'ok', 'fine']):
        return 'neutral'
    elif any(word in text_lower for word in ['curious', 'interesting', 'why', 'how', 'wonder']):
        return 'curious'
    
    return 'neutral'

def calculate_casual_ratio(recent_history):
    """Calculate the ratio of casual vs academic conversations."""
    if not recent_history:
        return 0
    
    casual_count = 0
    for msg in recent_history:
        if msg.role == "user" and not msg.hasScore:
            intent = detect_conversation_intent(msg.content)
            if intent in ['casual', 'help']:
                casual_count += 1
    
    return casual_count / len([msg for msg in recent_history if msg.role == "user"])


def detect_subject_from_text(text):
    """Detect subject from text content."""
    text = text.lower()
    if any(keyword in text for keyword in ['math', 'equation', 'integral', 'calculus', 'algebra', 'derivative']):
        return 'mathematics'
    elif any(keyword in text for keyword in ['physics', 'force', 'motion', 'energy', 'velocity']):
        return 'physics'
    elif any(keyword in text for keyword in ['chemistry', 'molecule', 'compound', 'reaction', 'atom']):
        return 'chemistry'
    elif any(keyword in text for keyword in ['biology', 'cell', 'organism', 'gene', 'dna']):
        return 'biology'
    return 'general'

def build_contextual_prompt_enhancement(chat_context: ChatContext, current_subject: str):
    """Build enhanced prompt section based on chat history."""
    if not chat_context:
        return ""
    
    context_analysis = analyze_conversation_context(chat_context)
    
    enhancement = "\n\n=== CONVERSATION CONTEXT ===\n"
    
    # Add conversation length context
    if context_analysis.get("conversation_length", 0) > 1:
        enhancement += f"This is part of an ongoing conversation with {context_analysis['conversation_length']} messages. "
    
    # Add subject continuity
    recent_subjects = context_analysis.get("recent_subjects", [])
    if recent_subjects:
        enhancement += f"Recent subjects discussed: {', '.join(recent_subjects)}. "
    
    # Add learning progression insight
    progression = context_analysis.get("learning_progression", [])
    if len(progression) >= 2:
        recent_scores = progression[-3:]  # Last 3 scores
        avg_recent = sum(s["percentage"] for s in recent_scores) / len(recent_scores)
        if avg_recent > 80:
            enhancement += "The student has been performing well recently (>80% average). "
        elif avg_recent < 50:
            enhancement += "The student has been struggling recently (<50% average). Provide extra encouragement and clearer explanations. "
      # Add mood and topic context
    topics = context_analysis.get("conversation_topics", [])
    if topics:
        enhancement += f"Recent conversation themes: {', '.join(set(topics))}. "
    
    mood_indicators = context_analysis.get("student_mood_indicators", [])
    if mood_indicators:
        latest_mood = mood_indicators[-1]
        enhancement += f"Student's recent mood: {latest_mood}. "
    # Add interaction pattern insights
    patterns = context_analysis.get("interaction_patterns", {})
    if patterns.get("multi_modal_learner"):
        enhancement += "This student uses multiple input methods (images, voice, files) - they may be a visual/kinesthetic learner. "
    
    # Add recent conversation context (last 3 messages)
    if chat_context.recentHistory:
        enhancement += "\n\nRECENT CONVERSATION:\n"
        for msg in chat_context.recentHistory[-3:]:
            role_label = "Student" if msg.role == "user" else "Teacher"
            content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            enhancement += f"{role_label}: {content_preview}\n"
            
            # Add context about media
            if msg.hasImage:
                enhancement += f"  [Included image: {msg.imageName}]\n"
            if msg.hasFile:
                enhancement += f"  [Included file: {msg.fileName}]\n"
            if msg.hasVoice:
                enhancement += f"  [Voice input used]\n"
            if msg.hasScore:
                enhancement += f"  [Score: {msg.score}/{msg.totalMarks}]\n"
    
    enhancement += "\n=== END CONTEXT ===\n\n"
    enhancement += f"Given this conversation context, please provide feedback that builds upon previous discussions and addresses the student's demonstrated learning patterns and needs.\n"
    
    return enhancement

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
            "temperature": 0.7,
            "topP": 0.95,
            "topK": 80,
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
                    "mime_type": "image/jpeg",
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

# Extract text from image bytes
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

def format_evaluation_prompt(question, student_answer, subject, grade, total_marks, chat_context=None ,current_subject="general"):
    """Create a detailed prompt for Gemini to evaluate student solutions with thorough, teacher-like feedback."""
    # Build contextual enhancement
    context_enhancement = ""
    if chat_context:
        context_enhancement = build_contextual_prompt_enhancement(chat_context, current_subject)
    prompt = f"""
You are an expert educational evaluator for K-12 students. Your role is to carefully analyze solutions and provide constructive, detailed feedback and correct answer if they are making mistakes that helps students learn and improve.
{context_enhancement}
QUESTION:
{question}

STUDENT'S ANSWER:
{student_answer}

TOTAL MARKS: {total_marks}
SUBJECT: {subject}
GRADE LEVEL: {grade}
CURRENT SUBJECT FOCUS:{current_subject}

When evaluating this solution:
1. **Contextual Awareness**: If this is part of an ongoing conversation, reference previous discussions when relevant and build upon established understanding.
2. Begin with a short summary acknowledging the student's strengths - what concepts they understood correctly and applied well.

3. Perform a detailed step-by-step analysis of the solution:
   - Identify each logical step in the student's work
   - For each step, analyze its mathematical/scientific correctness 
   - Point out where precise reasoning was demonstrated
   - Identify any conceptual errors or procedural mistakes

4. For any errors found:
   - Clearly explain what the specific mistake is
   - Why it's mathematically/scientifically incorrect 
   - Show the correct approach with explicit calculations
   - Connect the correction to fundamental principles

5. Look for areas of improvement even in correct solutions:
   - More efficient solution methods
   - Better organization or presentation
   - Opportunities for deeper mathematical/scientific insight
   - Alternative approaches worth considering

6. Score the solution fairly based on:
   - Correctness of key steps
   - Proper application of concepts
   - Completeness of the solution
   - Mathematical/scientific reasoning demonstrated

7. Provide specific, actionable recommendations that will help the student:
   - Strengthen conceptual understanding
   - Improve problem-solving techniques
   - Develop better solution presentation skills
   - Gain deeper insights into the subject matter

8. For the formatted_feedback, use this specific visual markdown format:
   -  **Question Recap**: Restate the question clearly.
   -  **Step-by-step Analysis**: Use ✅ / ⚠️ / ❌ with detailed breakdown.
   -  **Total Marks**: Use a markdown table like:
     | Criteria | Marks |
     |----------|-------|
     | Concept Understanding | 1 |
     | Substitution Accuracy | 2 |
   - 🟢 **Final Evaluation**: Give overall result (e.g. 🟢 Final Evaluation: Full Marks (6/6))
   - ✅ **Feedback**: List praises and improvement points if needed.

   
!!! IMPORTANT !!!
Your response MUST be a single valid JSON object that matches the following format exactly. Do NOT include plain text or explanations outside the JSON object.

{{
  "score": 5,
  "feedback": "Your summary here.",
  "detailed_analysis": {{
    "problem_understanding": "...",
    "approach_evaluation": "...",
    "step_by_step_analysis": [
      {{
        "step_number": 1,
        "step_description": "...",
        "student_work": "...",
        "correctness": "Correct / Partially Correct / Incorrect",
        "explanation": "...",
        "correction": "..."
      }}
    ],
    "conceptual_understanding": "...",
    "scoring_breakdown": [
      {{
        "component": "...",
        "marks_awarded": 1,
        "marks_possible": 1,
        "justification": "..."
      }}
    ],
    "correct_solution": "...",
    "improvement_suggestions": ["...", "..."]
  }},
  "formatted_feedback": "✅ Question Recap:...\n✅ Step-by-step:...\n📊 Score Table..."
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
11. The formatted_feedback field should have a visually appealing format with clear sections, appropriate use of emojis, and markdown formatting
12. **Use conversation context** to provide more personalized and progressive feedback
13. **Reference previous learning** when applicable to show continuity and growth
Remember that your goal is to help the student learn from this assessment, not just assign a score.
"""
    return prompt

async def evaluate_with_gemini(question, student_answer, subject, grade, total_marks, image_content=None, chat_context=None, current_subject="general"):
    """Use Gemini API to evaluate the answer, with optional image analysis."""
    prompt = format_evaluation_prompt(question, student_answer, subject, grade, total_marks, chat_context, current_subject)
    
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
            },
            "formatted_feedback": f"⚠️ **System is experiencing issues.**\n\nWe're unable to provide detailed feedback at the moment. Your answer has been recorded and will be evaluated later.\n\n📊 **Temporary Score**: {round(total_marks * 0.5, 1)}/{total_marks}"
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
        logger.info(f"Gemini raw JSON parsed: {json.dumps(evaluation_data, indent=2)}")

        # Ensure score is within bounds
        evaluation_data["score"] = max(0, min(float(evaluation_data["score"]), total_marks))
        evaluation_data["question"] = question
          # Add conversation context analysis if chat history was provided
        if chat_context:
            context_analysis = analyze_conversation_context(chat_context)
            if "contextual_insights" not in evaluation_data:
                evaluation_data["contextual_insights"] = {}
            evaluation_data["contextual_insights"]["conversation_analysis"] = context_analysis
        # If formatted_feedback is not provided, generate a basic one
        if ("formatted_feedback" not in evaluation_data or not evaluation_data["formatted_feedback"] or "step_by_step_analysis" not in evaluation_data.get("detailed_analysis", {})):
           evaluation_data["formatted_feedback"] = generate_formatted_feedback(evaluation_data, total_marks)
        
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
                    
                    # Generate formatted feedback if missing
                    if "formatted_feedback" not in evaluation_data or not evaluation_data["formatted_feedback"]:
                        evaluation_data["formatted_feedback"] = generate_formatted_feedback(evaluation_data, total_marks)
                    
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
        basic_feedback = f"⚠️ **Partial evaluation:** We encountered an issue processing the detailed feedback.\n\nBased on your answer, you've earned approximately {score}/{total_marks} marks."
        
        return {
            "feedback": basic_feedback,
            "score": score,
            "detailed_analysis": {
                "strengths": ["Analysis incomplete"],
                "weaknesses": ["Analysis incomplete"],
                "misconceptions": [],
                "corrections": [],
                "improvement_tips": ["Please ensure your answer is clear and complete"]
            },
            "formatted_feedback": basic_feedback
        }


def generate_formatted_feedback(evaluation_data, total_marks):
    """Generate a nicely formatted feedback from evaluation data if missing."""
    try:
        score = evaluation_data["score"]
        feedback = evaluation_data["feedback"]
        
        # Start building formatted feedback
        formatted = f"# ✅ Evaluation Summary\n\n"
        formatted += f"**Score: {score}/{total_marks}**\n\n"
        formatted += f"{feedback}\n\n"
        
        # Add detailed analysis if available
        if "detailed_analysis" in evaluation_data:
            analysis = evaluation_data["detailed_analysis"]
            
            # Problem understanding
            if "problem_understanding" in analysis:
                formatted += f"## ✅ Problem Understanding\n\n"
                formatted += f"{analysis['problem_understanding']}\n\n"
            
            # Approach evaluation
            if "approach_evaluation" in analysis:
                formatted += f"## 🔍 Approach Analysis\n\n"
                formatted += f"{analysis['approach_evaluation']}\n\n"
            
            # Step-by-step analysis
            if "step_by_step_analysis" in analysis and analysis["step_by_step_analysis"]:
                formatted += f"## ✅ Step-by-step Analysis\n\n"
                for step in analysis["step_by_step_analysis"]:
                    # Emoji based on correctness
                    emoji = "✅" if step.get("correctness", "").lower() == "correct" else "⚠️" if step.get("correctness", "").lower() == "partially correct" else "❌"
                    
                    formatted += f"### {emoji} Step {step.get('step_number', '?')}: {step.get('step_description', 'Analysis')}\n\n"
                    formatted += f"- **Student Work**: {step.get('student_work', 'N/A')}\n"
                    formatted += f"- **Evaluation**: {step.get('explanation', 'N/A')}\n"
                    
                    if step.get("correction") and step.get("correctness", "").lower() != "correct":
                        formatted += f"- **Correction**: {step.get('correction', '')}\n"
                    
                    formatted += "\n"
            
            # Scoring breakdown
            if "scoring_breakdown" in analysis and analysis["scoring_breakdown"]:
                formatted += f"## 📊 Score Breakdown\n\n"
                formatted += "| Component | Marks Awarded | Marks Possible | Justification |\n"
                formatted += "|-----------|--------------|---------------|---------------|\n"
                
                for component in analysis["scoring_breakdown"]:
                    formatted += f"| {component.get('component', 'N/A')} | {component.get('marks_awarded', 0)} | {component.get('marks_possible', 1)} | {component.get('justification', 'N/A')} |\n"
                
                formatted += "\n"
            
            # Correct solution
            if "correct_solution" in analysis and analysis["correct_solution"]:
                formatted += f"## 📝 Complete Solution\n\n"
                formatted += f"{analysis['correct_solution']}\n\n"
            
            # Improvement suggestions
            if "improvement_suggestions" in analysis and analysis["improvement_suggestions"]:
                formatted += f"## 💡 Improvement Suggestions\n\n"
                for i, suggestion in enumerate(analysis["improvement_suggestions"], 1):
                    formatted += f"{i}. {suggestion}\n"
                formatted += "\n"
            
            # Final evaluation
            final_score_percentage = (score / total_marks) * 100
            if final_score_percentage >= 90:
                formatted += f"## 🟢 Final Evaluation: **Excellent!** ({score}/{total_marks})\n\n"
            elif final_score_percentage >= 80:
                formatted += f"## 🟢 Final Evaluation: **Very Good!** ({score}/{total_marks})\n\n"
            elif final_score_percentage >= 70:
                formatted += f"## 🟡 Final Evaluation: **Good** ({score}/{total_marks})\n\n"
            elif final_score_percentage >= 50:
                formatted += f"## 🟠 Final Evaluation: **Satisfactory** ({score}/{total_marks})\n\n"
            else:
                formatted += f"## 🔴 Final Evaluation: **Needs Improvement** ({score}/{total_marks})\n\n"
        
        return formatted
    
    except Exception as e:
        logger.error(f"Error generating formatted feedback: {e}")
        return f"# Evaluation Result\n\nScore: {evaluation_data.get('score', 0)}/{total_marks}\n\n{evaluation_data.get('feedback', 'No detailed feedback available.')}"
    
def detect_conversation_intent(user_message: str) -> str:
    """
    Detect if the user message is casual conversation or needs evaluation.
    Returns: 'casual', 'evaluation', or 'help'
    """
    message_lower = user_message.lower().strip()
    
    # Casual conversation patterns
    casual_patterns = [
        # Greetings
        r'\b(hi|hello|hey|good morning|good afternoon|good evening)\b',
        # Thanks/acknowledgments
        r'\b(thank you|thanks|thanku|thx|okay|ok|alright|got it|understood)\b',
        # Simple responses
        r'^(yes|no|sure|fine|cool|nice|great|awesome)\.?!?$',
        # Goodbye
        r'\b(bye|goodbye|see you|later|take care)\b',
        # Just punctuation or very short
        r'^[.!?]{1,3}$'
    ]
    
    # Check if it's casual conversation
    for pattern in casual_patterns:
        if re.search(pattern, message_lower):
            return 'casual'
    
    # Help requests
    help_patterns = [
        r'\b(help|how to|what is|explain|don\'t understand|confused)\b',
        r'\b(can you help|need help|assistance)\b'
    ]
    
    for pattern in help_patterns:
        if re.search(pattern, message_lower):
            return 'help'
    
    # Check if it looks like a math problem (contains numbers, math symbols, etc.)
    math_indicators = [
        r'\d+',  # Contains numbers
        r'[+\-*/=<>]',  # Math operators
        r'\b(solve|calculate|find|equation|answer|problem)\b',
        r'\b(x|y|z)\s*[=+\-*/]',  # Variables with operators
        len(message_lower) > 20  # Longer messages more likely to be problems
    ]
    
    math_score = sum(1 for pattern in math_indicators if re.search(pattern, user_message))
    
    if math_score >= 2:  # At least 2 indicators suggest it's a math problem
        return 'evaluation'
    
    # Default to casual for short, unclear messages
    return 'casual'

async def generate_casual_response(user_message: str, chat_context: ChatContext = None) -> dict:
    """Generate a friendly, conversational response for casual messages."""
    message_lower = user_message.lower().strip()
    
    # Contextual responses based on chat history
    context_info = ""
    if chat_context and chat_context.recentHistory:
        recent_evaluations = [msg for msg in chat_context.recentHistory[-5:] if msg.hasScore]
        if recent_evaluations:
            context_info = f" I see we've been working on some problems together."
    
    # Response patterns
    if re.search(r'\b(thank you|thanks|thanku|thx)\b', message_lower):
        responses = [
            f"You're welcome! 😊{context_info} Feel free to ask if you need help with any math problems.",
            f"Happy to help!{context_info} What would you like to work on next?",
            f"No problem at all!{context_info} I'm here whenever you need assistance with your studies."
        ]
    elif re.search(r'\b(hi|hello|hey)\b', message_lower):
        responses = [
            f"Hello! 👋{context_info} Ready to tackle some math problems together?",
            f"Hi there!{context_info} What can I help you with today?",
            f"Hey! 😊{context_info} Let's dive into some learning!"
        ]
    elif re.search(r'\b(okay|ok|alright|got it|understood)\b', message_lower):
        responses = [
            f"Great!{context_info} Do you have another problem you'd like me to help with?",
            f"Perfect! 👍{context_info} What's next on your learning agenda?",
            f"Awesome!{context_info} Ready for the next challenge?"
        ]
    elif re.search(r'\b(bye|goodbye|see you|later)\b', message_lower):
        responses = [
            f"Goodbye! 👋{context_info} Keep up the great work with your studies!",
            f"See you later!{context_info} Remember, practice makes perfect! 📚",
            f"Take care!{context_info} I'll be here when you need help again."
        ]
    else:
        # Generic friendly response
        responses = [
            f"I'm here to help you with math problems and learning! 📚{context_info} What would you like to work on?",
            f"Hey there!{context_info} Share a problem you're working on, and I'll help you solve it step by step! ✨",
            f"Ready to learn together!{context_info} Feel free to ask me about any math concepts or problems. 🤓"
        ]
    
    import random
    response_text = random.choice(responses)
    
    return {
        "feedback": response_text,
        "score": None,  # No scoring for casual conversation
        "detailed_analysis": None,
        "formatted_feedback": f"\n\n{response_text}",
        "conversation_type": "casual"
    }

async def generate_help_response(user_message: str, chat_context: ChatContext = None) -> dict:
    """Generate helpful response for help requests."""
    help_text = """
🎓 **I'm your AI Math Tutor!** Here's how I can help:

📝 **Submit Problems**: Send me math questions and your solutions
📸 **Image Support**: Upload photos of handwritten work
🔍 **Step-by-Step**: I'll analyze each step of your solution
📊 **Detailed Feedback**: Get scores and improvement suggestions
💡 **Learning Tips**: Receive personalized study advice

**Example**: 
- *Question*: "Solve 2x + 5 = 15"
- *Your Answer*: "x = 5"
- I'll evaluate your work and provide detailed feedback!

What math problem would you like help with? 🤔
    """
    
    return {
        "feedback": help_text,
        "score": None,
        "detailed_analysis": None,
        "formatted_feedback": help_text,
        "conversation_type": "help"
    }

# API endpoints
@router.post("/evaluate-text")
async def evaluate_text_endpoint(request: dict = Body(...)):
    """Evaluate a problem from text input using Gemini API with chat history support."""
    try:
        # Log incoming request for debugging
        logger.info(f"Received evaluation request: {request}")
        
        # Extract and validate required fields
        user_message = request.get("studentAnswer", "")
        question = request.get("question", "")
        student_answer = request.get("studentAnswer", "")
        total_marks = request.get("totalMarks", 1)
        subject = request.get("subject", "mathematics")
        grade = request.get("grade", 10)
        current_subject = request.get("currentSubject", "general")
        has_voice_input = request.get("hasVoiceInput", False)
         # Extract and parse chat history
        chat_history_data = request.get("chatHistory")
        chat_context = parse_chat_history(chat_history_data)

           # Log chat context information
        if chat_context:
            logger.info(f"Chat context found with {chat_context.totalMessages} total messages")
            logger.info(f"Recent history length: {len(chat_context.recentHistory)}")
        else:
            logger.info("No chat context provided")
        # Validate input
        if not student_answer:
            logger.warning("Missing student answer in request")
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Student answer is required for evaluation", 
                    "feedback": "No answer provided", 
                    "score": 0,
                    "formatted_feedback": "❌ **Missing Answer**\n\nYou didn't provide an answer to evaluate."
                }
            )
        chat_history_data = request.get("chatHistory")
        chat_context = parse_chat_history(chat_history_data)
         # Detect conversation intent
        intent = detect_conversation_intent(user_message)
        logger.info(f"Detected intent: {intent} for message: '{user_message[:50]}...'")
        
        # Handle based on intent
        if intent == 'casual':
            return await generate_casual_response(user_message, chat_context)
        elif intent == 'help':
            return await generate_help_response(user_message, chat_context)
        elif intent == 'evaluation':
            # Proceed with existing evaluation logic
            total_marks = request.get("totalMarks", 1)
            subject = request.get("subject", "mathematics")
            grade = request.get("grade", 10)
            current_subject = request.get("currentSubject", "general")
            
            # Check if we have a proper question
            if not question.strip():
                return JSONResponse(
                    content={
                        "feedback": "I'd love to help! Could you please provide the math question you're working on? 📝",
                        "score": None,
                        "formatted_feedback": "❓ **Missing Question**\n\nI'd love to help! Could you please provide the math question you're working on? 📝\n\n**Example Format:**\n- Question: Solve 2x + 5 = 15\n- Your Answer: [your solution]"
                    }
                )
        # Log extracted parameters
        logger.info(f"Processing with: question='{question}', answer='{student_answer}', marks={total_marks}")
        
        # Evaluate using Gemini
        evaluation = await evaluate_with_gemini(
            question=question,
            student_answer=student_answer,
            subject=subject,
            grade=grade,
            total_marks=total_marks,
            chat_context=chat_context,
            current_subject=current_subject
        )
        
        return evaluation
    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        # Return a more helpful error response
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Evaluation error: {str(e)}", 
                "feedback": "System error occurred", 
                "score": 0,
                "formatted_feedback": "❌ **System Error**\n\nWe encountered a problem while evaluating your answer. Please try again later."
            }
        )

# Enhanced evaluate with image endpoint
@router.post("/evaluate/with-image", response_model=EvaluationResponse)
async def evaluate_with_image(
    question: str = Form(...),
    totalMarks: int = Form(...),
    studentAnswer: Optional[str] = Form(""),
    subject: str = Form("mathematics"),
    grade: int = Form(10),
    currentSubject: Optional[str] = Form("general"),
    chatHistory: Optional[str] = Form(None),
    hasVoiceInput: Optional[bool] = Form(False),
    answerImage: Optional[UploadFile] = File(None),
    questionImage: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None)  # Generic file field for compatibility
):
    """Evaluate a problem using text and/or images using Gemini API  with chat history support."""
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
         # Parse chat history
        chat_context = parse_chat_history(chatHistory)
        if chat_context:
            logger.info(f"Chat context found with {chat_context.totalMessages} total messages")
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
                    "score": 0,
                    "formatted_feedback": "❌ **Missing Answer**\n\nYou didn't provide an answer (text or image) to evaluate."
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
            image_content=image_for_gemini,
            chat_context=chat_context,
            current_subject=currentSubject or "general"
        )
        
        return evaluation
    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Evaluation error: {str(e)}",
                "feedback": "An error occurred while processing your submission.",
                "score": 0,
                "formatted_feedback": "❌ **System Error**\n\nWe encountered a problem while evaluating your answer. Please try again later."
            }
        )

# New endpoint for direct image evaluation without text
@router.post("/evaluate/image-answer", response_model=EvaluationResponse)
async def evaluate_image_answer(
    question: str = Form(...),
    totalMarks: int = Form(...),
    subject: str = Form("mathematics"),
    grade: int = Form(10),
    currentSubject: Optional[str] = Form("general"),
    chatHistory: Optional[str] = Form(None),
    hasVoiceInput: Optional[bool] = Form(False),
    image: UploadFile = File(...)
):
    """Evaluate a student answer provided as an image with chat history support."""
    try:
        # Log incoming request
        logger.info(f"Received image evaluation request for question: {question}")
    
         # Parse chat history
        chat_context = parse_chat_history(chatHistory)
        if chat_context:
            logger.info(f"Chat context found with {chat_context.totalMessages} total messages")
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
            image_content=image_content,  # Pass the raw image to Gemini
            chat_context=chat_context,
            current_subject=currentSubject or "general"
        )
        
        return evaluation
    except Exception as e:
        logger.error(f"Image evaluation error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Image evaluation error: {str(e)}",
                "feedback": "An error occurred while processing your image submission.",
                "score": 0,
                "formatted_feedback": "❌ **Image Processing Error**\n\nWe encountered a problem while evaluating your image answer. Please try again later."
            }
        )


# Subject-specific evaluation endpoints
@router.post("/evaluate/subject/{subject}", response_model=EvaluationResponse)
async def evaluate_by_subject(
    subject: str,
    request: TextEvaluationRequest
):
    """
    Evaluate a problem for a specific subject area with chat history support.
    Subjects can be: mathematics, physics, chemistry, biology, etc.
    """
    try:
        # Set the subject from the path parameter
        request.subject = subject
         # Parse chat history from request
        chat_context = parse_chat_history(request.chatHistory)
        if chat_context:
            logger.info(f"Chat context found with {chat_context.totalMessages} total messages for subject {subject}")
        
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
            total_marks=request.totalMarks,
            chat_context=chat_context,
            current_subject=request.currentSubject or subject
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
    currentSubject: Optional[str] = Form(None),
    chatHistory: Optional[str] = Form(None),
    hasVoiceInput: Optional[bool] = Form(False),
    answerImage: Optional[UploadFile] = File(None)
):
    """Evaluate a subject-specific problem with image support and chat history."""
    try:
        # Log request
        logger.info(f"Subject-specific image evaluation for {subject}: question='{question}'")
        
           # Parse chat history
        chat_context = parse_chat_history(chatHistory)
        if chat_context:
            logger.info(f"Chat context found with {chat_context.totalMessages} total messages for subject {subject}")
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
            image_content=answer_image_content,
            chat_context=chat_context,
            current_subject=currentSubject or subject
        )
        
        return evaluation
    except Exception as e:
        logger.error(f"Subject evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Subject evaluation error: {str(e)}")

# Add health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint to verify the service is running with chat history support."""
    try:
        # Check if OCR is available
        ocr_status = "available" if get_ocr_reader() is not None else "unavailable"
        
        # Test chat history parsing
        test_chat_data = {
            "recentHistory": [
                {
                    "role": "user",
                    "content": "Test message",
                    "timestamp": int(time.time())
                }
            ],
            "totalMessages": 1
        }
        
        try:
            test_context = parse_chat_history(test_chat_data)
            chat_history_status = "available" if test_context else "unavailable"
        except:
            chat_history_status = "error"
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "ocr_status": ocr_status,
            "chat_history_status": chat_history_status,
            "features": {
                "text_evaluation": True,
                "image_evaluation": True,
                "chat_history_support": True,
                "subject_specific_evaluation": True,
                "comprehensive_evaluation": True,
                "conversation_context_analysis": True
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(e)}
        )