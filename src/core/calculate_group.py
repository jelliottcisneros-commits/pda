def religion_data_percent(all_score_id):
    sensitivity = list()
    oneness = list()
    strength = list()
    appreciation = list()
    leveraged = list()
    for item in all_score_id:
        sensitivity_data = item.Religion_Score.sensitivity
        sensitivity.append(sensitivity_data)
        oneness_data = item.Religion_Score.oneness
        oneness.append(oneness_data)
        strength_data = item.Religion_Score.strength
        strength.append(strength_data)
        appreciation_data = item.Religion_Score.appreciation
        appreciation.append(appreciation_data)
        leveraged_data = item.Religion_Score.leveraged
        leveraged.append(leveraged_data)

    sensitivity_avg = sum(sensitivity) / len(sensitivity)
    sensitivity_per = round((sensitivity_avg * 100) / 8, 1)

    oneness_avg = sum(oneness) / len(oneness)
    oneness_per = round((oneness_avg * 100) / 8, 1)

    strength_avg = sum(strength) / len(strength)
    strength_per = round((strength_avg * 100) / 8, 1)

    appreciation_avg = sum(appreciation) / len(appreciation)
    appreciation_per = round((appreciation_avg * 100) / 8, 1)

    leveraged_avg = sum(leveraged) / len(leveraged)
    leveraged_per = round((leveraged_avg * 100) / 8, 1)

    religion_data_per = [(sensitivity_per, oneness_per, strength_per, appreciation_per, leveraged_per)]
    return religion_data_per


def disability_data_percent(all_score_id):
    sensitivity = list()
    oneness = list()
    strength = list()
    appreciation = list()
    leveraged = list()
    for item in all_score_id:
        sensitivity_data = item.Disability_Score.sensitivity
        sensitivity.append(sensitivity_data)
        oneness_data = item.Disability_Score.oneness
        oneness.append(oneness_data)
        strength_data = item.Disability_Score.strength
        strength.append(strength_data)
        appreciation_data = item.Disability_Score.appreciation
        appreciation.append(appreciation_data)
        leveraged_data = item.Disability_Score.leveraged
        leveraged.append(leveraged_data)

    disability_sensitivity_avg = sum(sensitivity) / len(sensitivity)
    disability_sensitivity_per = round((disability_sensitivity_avg * 100) / 8, 1)

    disability_oneness_avg = sum(oneness) / len(oneness)
    disability_oneness_per = round((disability_oneness_avg * 100) / 8, 1)

    disability_strength_avg = sum(strength) / len(strength)
    disability_strength_per = round((disability_strength_avg * 100) / 8, 1)

    disability_appreciation_avg = sum(appreciation) / len(appreciation)
    disability_appreciation_per = round((disability_appreciation_avg * 100) / 8, 1)

    disability_leveraged_avg = sum(leveraged) / len(leveraged)
    disability_leveraged_per = round((disability_leveraged_avg * 100) / 8, 1)

    disablity_data_per = [(disability_sensitivity_per, disability_oneness_per, disability_strength_per,
                           disability_appreciation_per, disability_leveraged_per)]

    return disablity_data_per


def culture_data_percent(all_score_id):
    culture_score_sensitivity = list()
    culture_score_oneness = list()
    culture_score_strength = list()
    culture_score_appreciation = list()
    culture_score_leveraged = list()
    for item in all_score_id:
        sensitivity_data = item.Culture_Score.sensitivity
        culture_score_sensitivity.append(sensitivity_data)
        oneness_data = item.Culture_Score.oneness
        culture_score_oneness.append(oneness_data)
        strength_data = item.Culture_Score.strength
        culture_score_strength.append(strength_data)
        appreciation_data = item.Culture_Score.appreciation
        culture_score_appreciation.append(appreciation_data)
        leveraged_data = item.Culture_Score.leveraged
        culture_score_leveraged.append(leveraged_data)

    culture_sensitivity_avg = sum(culture_score_sensitivity) / len(culture_score_sensitivity)
    culture_sensitivity_per = round((culture_sensitivity_avg * 100) / 8, 1)

    culture_oneness_avg = sum(culture_score_oneness) / len(culture_score_oneness)
    culture_oneness_per = round((culture_oneness_avg * 100) / 8, 1)

    culture_strength_avg = sum(culture_score_strength) / len(culture_score_strength)
    culture_strength_per = round((culture_strength_avg * 100) / 8, 1)

    culture_appreciation_avg = sum(culture_score_appreciation) / len(culture_score_appreciation)
    culture_appreciation_per = round((culture_appreciation_avg * 100) / 8, 1)

    culture_leveraged_avg = sum(culture_score_leveraged) / len(culture_score_leveraged)
    culture_leveraged_per = round((culture_leveraged_avg * 100) / 8, 1)

    culture_data_per = [(culture_sensitivity_per, culture_oneness_per, culture_strength_per,
                         culture_appreciation_per, culture_leveraged_per)]

    return culture_data_per


def gender_data_percent(all_score_id):
    sensitivity = list()
    oneness = list()
    strength = list()
    appreciation = list()
    leveraged = list()
    for item in all_score_id:
        sensitivity_data = item.Gender_Score.sensitivity
        sensitivity.append(sensitivity_data)
        oneness_data = item.Gender_Score.oneness
        oneness.append(oneness_data)
        strength_data = item.Gender_Score.strength
        strength.append(strength_data)
        appreciation_data = item.Gender_Score.appreciation
        appreciation.append(appreciation_data)
        leveraged_data = item.Gender_Score.leveraged
        leveraged.append(leveraged_data)

    sensitivity_avg = sum(sensitivity) / len(sensitivity)
    sensitivity_per = round((sensitivity_avg * 100) / 8, 1)

    oneness_avg = sum(oneness) / len(oneness)
    oneness_per = round((oneness_avg * 100) / 8, 1)

    strength_avg = sum(strength) / len(strength)
    strength_per = round((strength_avg * 100) / 8, 1)

    appreciation_avg = sum(appreciation) / len(appreciation)
    appreciation_per = round((appreciation_avg * 100) / 8, 1)

    leveraged_avg = sum(leveraged) / len(leveraged)
    leveraged_per = round((leveraged_avg * 100) / 8, 1)

    data_per = [(sensitivity_per, oneness_per, strength_per, appreciation_per, leveraged_per)]

    return data_per


def race_data_percent(all_score_id):
    sensitivity = list()
    oneness = list()
    strength = list()
    appreciation = list()
    leveraged = list()
    for item in all_score_id:
        sensitivity_data = item.Race_Score.sensitivity
        sensitivity.append(sensitivity_data)
        oneness_data = item.Race_Score.oneness
        oneness.append(oneness_data)
        strength_data = item.Race_Score.strength
        strength.append(strength_data)
        appreciation_data = item.Race_Score.appreciation
        appreciation.append(appreciation_data)
        leveraged_data = item.Race_Score.leveraged
        leveraged.append(leveraged_data)

    sensitivity_avg = sum(sensitivity) / len(sensitivity)
    sensitivity_per = round((sensitivity_avg * 100) / 8, 1)

    oneness_avg = sum(oneness) / len(oneness)
    oneness_per = round((oneness_avg * 100) / 8, 1)

    strength_avg = sum(strength) / len(strength)
    strength_per = round((strength_avg * 100) / 8, 1)

    appreciation_avg = sum(appreciation) / len(appreciation)
    appreciation_per = round((appreciation_avg * 100) / 8, 1)

    leveraged_avg = sum(leveraged) / len(leveraged)
    leveraged_per = round((leveraged_avg * 100) / 8, 1)

    data_per = [(sensitivity_per, oneness_per, strength_per, appreciation_per, leveraged_per)]

    return data_per


def class_data_percent(all_score_id):
    sensitivity = list()
    oneness = list()
    strength = list()
    appreciation = list()
    leveraged = list()
    for item in all_score_id:
        sensitivity_data = item.Class_Score.sensitivity
        sensitivity.append(sensitivity_data)
        oneness_data = item.Class_Score.oneness
        oneness.append(oneness_data)
        strength_data = item.Class_Score.strength
        strength.append(strength_data)
        appreciation_data = item.Class_Score.appreciation
        appreciation.append(appreciation_data)
        leveraged_data = item.Class_Score.leveraged
        leveraged.append(leveraged_data)

    sensitivity_avg = sum(sensitivity) / len(sensitivity)
    sensitivity_per = round((sensitivity_avg * 100) / 8, 1)

    oneness_avg = sum(oneness) / len(oneness)
    oneness_per = round((oneness_avg * 100) / 8, 1)

    strength_avg = sum(strength) / len(strength)
    strength_per = round((strength_avg * 100) / 8, 1)

    appreciation_avg = sum(appreciation) / len(appreciation)
    appreciation_per = round((appreciation_avg * 100) / 8, 1)

    leveraged_avg = sum(leveraged) / len(leveraged)
    leveraged_per = round((leveraged_avg * 100) / 8, 1)

    data_per = [(sensitivity_per, oneness_per, strength_per, appreciation_per, leveraged_per)]

    return data_per


def sexual_data_percent(all_score_id):
    sensitivity = list()
    oneness = list()
    strength = list()
    appreciation = list()
    leveraged = list()
    for item in all_score_id:
        sensitivity_data = item.Sexual_Orientation_Score.sensitivity
        sensitivity.append(sensitivity_data)
        oneness_data = item.Sexual_Orientation_Score.oneness
        oneness.append(oneness_data)
        strength_data = item.Sexual_Orientation_Score.strength
        strength.append(strength_data)
        appreciation_data = item.Sexual_Orientation_Score.appreciation
        appreciation.append(appreciation_data)
        leveraged_data = item.Sexual_Orientation_Score.leveraged
        leveraged.append(leveraged_data)

    sensitivity_avg = sum(sensitivity) / len(sensitivity)
    sensitivity_per = round((sensitivity_avg * 100) / 8, 1)

    oneness_avg = sum(oneness) / len(oneness)
    oneness_per = round((oneness_avg * 100) / 8, 1)

    strength_avg = sum(strength) / len(strength)
    strength_per = round((strength_avg * 100) / 8, 1)

    appreciation_avg = sum(appreciation) / len(appreciation)
    appreciation_per = round((appreciation_avg * 100) / 8, 1)

    leveraged_avg = sum(leveraged) / len(leveraged)
    leveraged_per = round((leveraged_avg * 100) / 8, 1)

    data_per = [(sensitivity_per, oneness_per, strength_per, appreciation_per, leveraged_per)]

    return data_per


def total_data_percent(all_score_id):
    sensitivity = list()
    oneness = list()
    strength = list()
    appreciation = list()
    leveraged = list()
    for item in all_score_id:
        sensitivity_data = item.sensitivity_total
        sensitivity.append(sensitivity_data)
        oneness_data = item.oneness_total
        oneness.append(oneness_data)
        strength_data = item.strength_total
        strength.append(strength_data)
        appreciation_data = item.appreciation_total
        appreciation.append(appreciation_data)
        leveraged_data = item.leveraged_total
        leveraged.append(leveraged_data)

    sensitivity_avg = sum(sensitivity) / len(sensitivity)
    sensitivity_per = round((sensitivity_avg * 100) / 56, 1)

    oneness_avg = sum(oneness) / len(oneness)
    oneness_per = round((oneness_avg * 100) / 56, 1)

    strength_avg = sum(strength) / len(strength)
    strength_per = round((strength_avg * 100) / 56, 1)

    appreciation_avg = sum(appreciation) / len(appreciation)
    appreciation_per = round((appreciation_avg * 100) / 56, 1)

    leveraged_avg = sum(leveraged) / len(leveraged)
    leveraged_per = round((leveraged_avg * 100) / 56, 1)

    data_per = [(sensitivity_per, oneness_per, strength_per, appreciation_per, leveraged_per)]

    return data_per


def calculate(category, all_score_id):
    if category == "Religion_Score":
        result = religion_data_percent(all_score_id)
    elif category == "Disability_Score":
        result = disability_data_percent(all_score_id)
    elif category == "Culture_Score":
        result = culture_data_percent(all_score_id)
    elif category == "Gender_Score":
        result = gender_data_percent(all_score_id)
    elif category == "Race_Score":
        result = race_data_percent(all_score_id)
    elif category == "Class_Score":
        result = class_data_percent(all_score_id)
    elif category == "Sexual_Orientation_Score":
        result = sexual_data_percent(all_score_id)
    elif category == "Total_Score":
        result = total_data_percent(all_score_id)
    return result


def calculate_leverage(all_score_id):
    TOTAL_COUNT = 56 * len(all_score_id)
    sensitivity = list()
    oneness = list()
    strength = list()
    appreciation = list()
    leveraged = list()
    for item in all_score_id:
        sensitivity_data = item.sensitivity_total
        sensitivity.append(sensitivity_data)
        oneness_data = item.oneness_total
        oneness.append(oneness_data)
        strength_data = item.strength_total
        strength.append(strength_data)
        appreciation_data = item.appreciation_total
        appreciation.append(appreciation_data)
        leveraged_data = item.leveraged_total
        leveraged.append(leveraged_data)

    sensitivity_total = sum(sensitivity)

    oneness_total = sum(oneness)

    strength_total = sum(strength)

    appreciation_total = sum(appreciation)
    leveraged_total = sum(leveraged)
    lev = TOTAL_COUNT - leveraged_total
    leveraged_difference = (sensitivity_total+oneness_total+strength_total+appreciation_total+lev)/(TOTAL_COUNT * 5)
    per_leveraged_difference = round((leveraged_difference * 100), 1)

    return per_leveraged_difference
