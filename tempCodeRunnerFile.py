       prompt = f"""Act as a professional nutritionist. Create a personalized 7-day diet plan for:
- Age: {user_data['age']}
- Gender: {user_data['sex']}
- Height: {user_data['height']} cm
- Weight: {user_data['weight']} kg
- Location: {user_data['state']}, {user_data['country']}
- Health Conditions: {', '.join(user_data['health_conditions']) if user_data.get('health_conditions') else "None"}
- Diet Preference: {diet_type}