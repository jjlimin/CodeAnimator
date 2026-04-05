balance = 100
actions = [20, -50, 100, -150]
print("Starting balance:")
print(balance)

for amount in actions:
    if amount > 0:
        print("Depositing...")
        balance = balance + amount
    else:
        print("Withdrawing...")
        if balance + amount < 0:
            print("Error: No money!")
        else:
            balance = balance + amount
    
    if balance > 150:
        print("High balance alert")
    
    print("Current balance:")
    print(balance)

print("Final status:")
if balance < 50:
    print("Account is low")
else:
    print("Account is healthy")

counter = 0
while counter < 3:
    print("Checking system...")
    counter = counter + 1