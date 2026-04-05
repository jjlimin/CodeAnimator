grades = [85, 42, 90, 60]
for grade in grades:
    print("Processing grade:")
    print(grade)
    if grade >= 90:
        result = "A"
    else:
        if grade >= 80:
            result = "B"
        else:
            if grade >= 60:
                result = "C"
            else:
                result = "F"
    
    print("Result:")
    print(result)
    if result == "F":
        print("Failed")