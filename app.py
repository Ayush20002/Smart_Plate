# Full Backend Code: app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
# Assuming you have a validation.py file with the validate_diet_input function
# Make sure it's updated if needed, although based on the requirement, no changes seem necessary there.
# from validation import validate_diet_input
import signal
import traceback # Added for better error logging

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS

# --- Mock Validation Function (Replace with your actual validation) ---
# If you don't have 'validation.py', you can use this placeholder or implement proper validation.
def validate_diet_input(user_data):
    errors = {}
    required_fields = ['age', 'sex', 'height', 'weight', 'state', 'country', 'diet_type']
    for field in required_fields:
        if field not in user_data or not user_data[field]:
            errors[field] = f"{field.capitalize()} is required."
    
    # Basic type/range checks (can be expanded)
    if 'age' in user_data and not isinstance(user_data['age'], int) or user_data.get('age', 0) < 1:
         errors['age'] = "Age must be a positive number."
    if 'height' in user_data and not isinstance(user_data['height'], (int, float)) or user_data.get('height', 0) <= 0:
         errors['height'] = "Height must be a positive number."
    if 'weight' in user_data and not isinstance(user_data['weight'], (int, float)) or user_data.get('weight', 0) <= 0:
         errors['weight'] = "Weight must be a positive number."
    if 'health_conditions' in user_data and not isinstance(user_data['health_conditions'], list):
         errors['health_conditions'] = "Health conditions should be a list of strings."
    if 'diet_type' in user_data and user_data['diet_type'].lower() not in ['veg', 'vegetarian', 'non-veg', 'non vegetarian']:
        errors['diet_type'] = "Invalid diet type specified."

    return errors
# --- End Mock Validation Function ---


# Configure Gemini with faster model
# Ensure your GEMINI_API_KEY is set in your .env file or environment variables
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set.")
genai.configure(api_key=api_key)

# It's generally better to initialize the model once if possible,
# but doing it here is fine for this structure.
# Using 'gemini-1.5-flash-latest' as 'gemini-2.0-flash' might not be a valid identifier
# Check available model names if issues arise.
try:
    model = genai.GenerativeModel('gemini-1.5-flash-latest') # Using a known valid model name
except Exception as e:
    print(f"Error initializing GenerativeModel: {e}")
    # Handle error appropriately, maybe exit or use a fallback
    raise

# Timeout handler for model response
class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Model response timed out")

# Set the signal handler for SIGALRM (used for timeouts)
# Note: signal.alarm is not available on Windows. Consider alternatives like threading.Timer if cross-platform compatibility is critical.
if hasattr(signal, 'SIGALRM'):
    signal.signal(signal.SIGALRM, timeout_handler)
else:
    print("Warning: signal.alarm is not available on this platform (e.g., Windows). Timeout functionality will be limited.")


@app.route('/')
def home():
    return "Diet Planner Backend Running!"

@app.route('/api/generate-diet', methods=['POST'])
def generate_diet():
    try:
        user_data = request.json
        if not user_data:
             return jsonify({"status": "error", "message": "Invalid request: No JSON data received."}), 400

        # Validate input (using the mock or your actual validation function)
        errors = validate_diet_input(user_data)
        if errors:
            return jsonify({"status": "error", "errors": errors}), 400

        # Determine the diet type description for prompt clarity
        diet_type_input = user_data.get('diet_type', 'veg').lower()
        if diet_type_input in ['veg', 'vegetarian']:
            diet_type = "vegetarian"
        elif diet_type_input in ['non-veg', 'non vegetarian']:
            diet_type = "non-vegetarian"
        else:
            # Defaulting to vegetarian if input is unexpected after validation (should ideally not happen)
            diet_type = "vegetarian"
            print(f"Warning: Unexpected diet_type '{diet_type_input}' received after validation. Defaulting to vegetarian.")

        # Ensure health conditions are passed as a string, or "None"
        health_conditions_str = "None"
        if user_data.get('health_conditions'):
             # Ensure it's a list of strings before joining
            if isinstance(user_data['health_conditions'], list):
                 # Filter out empty strings just in case
                 conditions = [str(cond).strip() for cond in user_data['health_conditions'] if str(cond).strip()]
                 if conditions:
                      health_conditions_str = ', '.join(conditions)
            else:
                 # Handle case where it might not be a list unexpectedly
                 print(f"Warning: health_conditions received was not a list: {user_data['health_conditions']}")


        # --- Updated Prompt ---
        prompt = f"""Act as a professional nutritionist. Create a personalized 7-day diet plan for:
- Age: {user_data.get('age', 'N/A')}
- Gender: {user_data.get('sex', 'N/A')}
- Height: {user_data.get('height', 'N/A')} cm
- Weight: {user_data.get('weight', 'N/A')} kg
- Location: {user_data.get('state', 'N/A')}, {user_data.get('country', 'N/A')}
- Health Conditions: {health_conditions_str}
- Diet Preference: {diet_type}

When creating the diet plan:
1. Use **consistent measurement units** for all volume measurements (e.g., use "cups" or "ml" consistently, specify which).
2. For snack options, provide a **variety of choices** and avoid repeating the exact same snack daily (e.g., offer fruits, yogurt, nuts, veggie sticks).
3. If any health conditions are provided (not "None"), include **specific advice and tailored recommendations** that address those conditions within the plan or in a dedicated section.
4. Ensure that the meal options adhere to the specified diet preference (i.e., all meals should be {diet_type}).
5. Do not repeat the exact same meal combination (e.g., Breakfast A, Lunch B, Dinner C) on different days. Variety is key. Avoid responses like "repeat Monday's Breakfast". Define each meal explicitly.
6. If the user selected non-vegetarian, include a mix of non-vegetarian and healthy vegetarian meals appropriate for the specified location. Don't make every meal non-veg.
7. For each meal (breakfast, lunch, snacks, dinner), include an estimated **glucose_spike_prediction** level based on the meal's composition and typical glycemic response. Use simple terms: "Low", "Moderate", or "High".

Provide the response ONLY in perfect JSON format without any surrounding text, comments, or markdown formatting (like ```json ... ```). Structure it exactly like this example:
{{
    "weekly_plan": {{
        "monday": {{
            "breakfast": {{"meal": "Oatmeal with Berries and Nuts", "calories": 350, "protein": "10g", "carbs": "50g", "fats": "12g", "glucose_spike_prediction": "Low"}},
            "lunch": {{"meal": "Lentil Soup with Whole Wheat Bread", "calories": 450, "protein": "20g", "carbs": "60g", "fats": "15g", "glucose_spike_prediction": "Moderate"}},
            "snacks": {{"meal": "Apple slices with Peanut Butter", "calories": 200, "protein": "5g", "carbs": "30g", "fats": "8g", "glucose_spike_prediction": "Low"}},
            "dinner": {{"meal": "Baked Salmon with Roasted Vegetables", "calories": 500, "protein": "35g", "carbs": "40g", "fats": "20g", "glucose_spike_prediction": "Low"}}
        }},
        "tuesday": {{
            "breakfast": {{"meal": "Scrambled Eggs with Spinach and Toast", "calories": 400, "protein": "25g", "carbs": "30g", "fats": "20g", "glucose_spike_prediction": "Low"}},
            "lunch": {{ "meal": "...", "calories": 0, ... , "glucose_spike_prediction": "..." }},
            "snacks": {{ "meal": "...", "calories": 0, ... , "glucose_spike_prediction": "..." }},
            "dinner": {{ "meal": "...", "calories": 0, ... , "glucose_spike_prediction": "..." }}
        }},
        "wednesday": {{ ... similar structure ... }},
        "thursday": {{ ... similar structure ... }},
        "friday": {{ ... similar structure ... }},
        "saturday": {{ ... similar structure ... }},
        "sunday": {{ ... similar structure ... }}
    }},
    "nutritional_goals": {{
        "daily_calories": 2000,
        "protein_grams": 100,
        "carb_grams": 250,
        "fat_grams": 60
    }},
    "recommended_foods": ["List", "of", "recommended", "foods"],
    "foods_to_avoid": ["List", "of", "foods", "to", "avoid"],
    "cooking_tips": ["Tip 1", "Tip 2", "Tip 3"],
    "cultural_considerations": "Specific notes based on location if applicable, otherwise brief general advice or empty string."
}}"""
        # --- End of Updated Prompt ---

        # Set timeout for model response (only if signal.alarm is available)
        response = None
        timed_out = False
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(45)  # Increased timeout to 45 seconds for potentially complex generation
            try:
                response = model.generate_content(prompt)
            except TimeoutException:
                timed_out = True
                print("Model response timed out.")
            finally:
                signal.alarm(0)  # Disable alarm
        else:
            # If alarm is not available, call directly without timeout
            try:
                 response = model.generate_content(prompt)
            except Exception as e:
                 print(f"Error during model generation (no timeout): {str(e)}")
                 return jsonify({
                     "status": "error",
                     "message": f"Error communicating with AI model: {str(e)}"
                 }), 500

        if timed_out:
             return jsonify({
                "status": "error",
                "message": "Model response timed out. The request took too long. Please try again, perhaps with simpler requirements."
             }), 504 # Gateway Timeout

        if not response or not hasattr(response, 'text'):
             print(f"Received invalid response from model: {response}")
             return jsonify({
                "status": "error",
                "message": "Received an invalid or empty response from the AI model."
             }), 502 # Bad Gateway

        # Clean the response text
        # Remove markdown code block fences and leading/trailing whitespace
        cleaned_response = response.text.strip()
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[len('```json'):]
        if cleaned_response.startswith('```'):
             cleaned_response = cleaned_response[len('```'):]
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-len('```')]
        cleaned_response = cleaned_response.strip()

        # Attempt to parse the JSON
        try:
            diet_plan = json.loads(cleaned_response)

            # Optional: Basic check if the model likely included the new field
            try:
                # Check a sample path; adjust if your structure differs slightly
                sample_meal = diet_plan.get("weekly_plan", {}).get("monday", {}).get("breakfast", {})
                if "glucose_spike_prediction" not in sample_meal:
                    print("Warning: Model response JSON parsed successfully, but 'glucose_spike_prediction' key is missing in sample meal (monday.breakfast). Check model's adherence to the prompt.")
                    # You could potentially add a default value here if needed, but it's better if the model provides it.
                    # e.g., diet_plan["weekly_plan"]["monday"]["breakfast"]["glucose_spike_prediction"] = "N/A"
            except Exception as check_e:
                 # Catch errors during the check itself (e.g., unexpected structure)
                 print(f"Warning: Could not perform check for 'glucose_spike_prediction' due to structure issue or error: {check_e}")


            return jsonify({
                "status": "success",
                "diet_plan": diet_plan
            })
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse JSON response from model.")
            print(f"JSONDecodeError: {str(e)}")
            print(f"Raw Response Text Received:\n---\n{cleaned_response}\n---")
            return jsonify({
                "status": "error",
                "message": f"Failed to parse the diet plan structure received from the AI. Please try again. Error: {str(e)}",
                # Optionally include the raw response in development/debugging, but be cautious in production
                # "raw_response": cleaned_response
            }), 500 # Internal Server Error

    except TimeoutException:
        # This catch block might be redundant if the inner try/finally handles it, but keep for safety
        print("Error: Model response timed out (caught outside inner block).")
        return jsonify({
            "status": "error",
            "message": "Model response timed out. Please try again."
        }), 504 # Gateway Timeout
    except Exception as e:
        print(f"Error generating diet plan: {str(e)}")
        print(traceback.format_exc()) # Print full traceback for debugging
        return jsonify({
            "status": "error",
            "message": f"An unexpected server error occurred: {str(e)}"
        }), 500 # Internal Server Error

if __name__ == '__main__':
    # Use threaded=True for handling multiple requests concurrently
    # Use debug=True for development (provides auto-reloading and more detailed errors)
    # Make sure to set debug=False in production
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), threaded=True, debug=False) # Set debug=False for production
