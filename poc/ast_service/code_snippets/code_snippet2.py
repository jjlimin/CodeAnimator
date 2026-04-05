total = 0
for i in range(1, 6):
    total = total + i
    if total > 5:
        print("Total is now big")
    else:
        print("Still small")

print("The final sum is:")
print(total)