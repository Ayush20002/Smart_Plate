from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from validation import validate_diet_input  # Ensure this validation handles the new "diet_type" parameter

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-pro')

@app.route('/')
def home():
    return "Diet Planner Backend Running!"

@app.route('/api/generate-diet', methods=['POST'])
def generate_diet():
    try:
        user_data = request.json
        
        # Validate input (make sure validate_diet_input now also checks for "diet_type")
        errors = validate_diet_input(user_data)
        if errors:
            return jsonify({"errors": errors}), 400

        # Determine the diet type description for prompt clarity
        diet_type = user_data.get('diet_type', 'veg').lower()  # Default to vegetarian if not provided
        if diet_type in ['veg', 'vegetarian']:
            diet_description = "vegetarian"
        elif diet_type in ['non-veg', 'non vegetarian']:
            diet_description = "non-vegetarian"
        else:
            diet_description = "vegetarian"  # fallback option

        # Create diet prompt with all modifications:
        # - Use consistent measurement units.
        # - Provide a variety of snack options.
        # - Include specific advice for health conditions if any.
        # - Generate a plan based on the diet type (vegetarian vs non-vegetarian).
        prompt = f"""Act as a professional nutritionist. Create a personalized 7-day diet plan for:
- Age: {user_data['age']}
- Gender: {user_data['sex']}
- Height: {user_data['height']} cm
- Weight: {user_data['weight']} kg
- Location: {user_data['state']}, {user_data['country']}
- Health Conditions: {', '.join(user_data['health_conditions']) if user_data.get('health_conditions') else "None"}
- Diet Preference: {diet_type}

When creating the diet plan:
1. Use **consistent measurement units** for all volume measurements. For example, use "cups" exclusively (avoid mixing with "glasses" or other units).
2. For snack options, provide a **variety of choices** and avoid repeating the same snack (for instance, do not list "Mixed Nuts" multiple times; instead, include options like fruits, yogurt, veggie sticks, etc.).
3. If any health conditions are provided, include **specific advice and tailored recommendations** that address those conditions.
4. Ensure that the meal options adhere to the specified diet preference (i.e., all meals should be {diet_type}).
5. Don't repeat the meal in any day so try to give repeat the meal on another day like it should not say like this:repeat Monday's Breakfast on particular day .
6. If user select non-vegeterian then dont only give non-veg meal also try to include veg meal that are healthy and present in that region.

Provide the response in perfect JSON format without any Markdown formatting. Structure it exactly like this:
{{
    "weekly_plan": {{
        "monday": {{
            "breakfast": {{"meal": "", "calories": 0, "protein": "0g", "carbs": "0g", "fats": "0g"}},
            "lunch": {{"meal": "", "calories": 0, "protein": "0g", "carbs": "0g", "fats": "0g"}},
            "dinner": {{"meal": "", "calories": 0, "protein": "0g", "carbs": "0g", "fats": "0g"}},
            "snacks": {{"meal": "", "calories": 0, "protein": "0g", "carbs": "0g", "fats": "0g"}}
        }},
        "tuesday": {{...}},
        "wednesday": {{...}},
        "thursday": {{...}},
        "friday": {{...}},
        "saturday": {{...}},
        "sunday": {{...}}
    }},
    "nutritional_goals": {{
        "daily_calories": 0,
        "protein_grams": 0,
        "carb_grams": 0,
        "fat_grams": 0
    }},
    "recommended_foods": [],
    "foods_to_avoid": [],
    "cooking_tips": [],
    "cultural_considerations": ""
}}"""

        # Generate and parse response
        response = model.generate_content(prompt)
        
        # Clean and parse the response
        cleaned_response = response.text.strip()
        cleaned_response = cleaned_response.replace('```json', '').replace('```', '')
        
        try:
            diet_plan = json.loads(cleaned_response)
            return jsonify({
                "status": "success",
                "diet_plan": diet_plan
            })
        except json.JSONDecodeError as e:
            return jsonify({
                "status": "error",
                "message": f"Failed to parse response: {str(e)}",
                "raw_response": cleaned_response
            }), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error generating diet plan: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run()
