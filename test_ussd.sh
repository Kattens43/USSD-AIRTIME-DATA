# Helper: define the base URL
URL="http://localhost:5050/ussd"
COMMON='-d sessionId=test1 -d serviceCode=*384*1234# -d phoneNumber=+254712345678'

# Turn 0: main menu
curl -s -X POST $URL $COMMON -d "text="
# Expected: CON Welcome to Acme Wallet ...

# Path 1: check balance
curl -s -X POST $URL $COMMON -d "text=1"
# Expected: END Your balance is KES 1,250.00

# Path 3: exit
curl -s -X POST $URL $COMMON -d "text=3"
# Expected: END Goodbye!

# Path 2: send money — step 1 (recipient prompt)
curl -s -X POST $URL $COMMON -d "text=2"
# Expected: CON Enter recipient phone number

# Step 2: amount prompt
curl -s -X POST $URL $COMMON -d "text=2*254798765432"
# Expected: CON Enter amount (KES)

# Step 3: confirmation prompt
curl -s -X POST $URL $COMMON -d "text=2*254798765432*500"
# Expected: CON Send KES 500 to 254798765432?...

# Step 4a: confirm
curl -s -X POST $URL $COMMON -d "text=2*254798765432*500*1"
# Expected: END Sent KES 500 to 254798765432. Thank you.

# Step 4b: cancel
curl -s -X POST $URL $COMMON -d "text=2*254798765432*500*2"
# Expected: END Transaction cancelled.

# Invalid: bad phone
curl -s -X POST $URL $COMMON -d "text=2*abc"
# Expected: END Invalid phone number. Please try again.

# Invalid: bad amount
curl -s -X POST $URL $COMMON -d "text=2*254798765432*abc"
# Expected: END Invalid amount.