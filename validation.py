def validate_diet_input(data):
    errors = []
    
    # Required fields including the new "diet_type"
    required_fields = ['age', 'sex', 'height', 'weight', 'country', 'state', 'health_conditions', 'diet_type']
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Validate numeric fields
    try:
        age = int(data['age'])
        if not 10 <= age <= 120:
            errors.append("Age must be between 10 and 120")
    except (ValueError, TypeError):
        errors.append("Invalid numeric value for age")
    
    try:
        height = float(data['height'])
        if not 100 <= height <= 250:
            errors.append("Height must be between 100 and 250 cm")
    except (ValueError, TypeError):
        errors.append("Invalid numeric value for height")
    
    try:
        weight = float(data['weight'])
        if not 30 <= weight <= 300:
            errors.append("Weight must be between 30 and 300 kg")
    except (ValueError, TypeError):
        errors.append("Invalid numeric value for weight")
    
    # Validate that health_conditions is a list
    if 'health_conditions' in data and not isinstance(data['health_conditions'], list):
        errors.append("Health conditions must be provided as a list")
    
    # Validate diet_type field
    allowed_diet_types = ['veg', 'vegetarian', 'non-veg', 'non vegetarian']
    if 'diet_type' in data:
        if not isinstance(data['diet_type'], str) or data['diet_type'].lower() not in allowed_diet_types:
            errors.append("Diet type must be one of: 'veg', 'vegetarian', 'non-veg', 'non vegetarian'")
    
    return errors
