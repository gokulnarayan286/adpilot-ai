
# AdPilot AI - Lesson 3
# Rule-based campaign decision engine

campaigns = [
    {"name": "Google Search", "spend": 5000, "installs": 1000, "purchases": 80},
    {"name": "Meta Prospecting", "spend": 8000, "installs": 1200, "purchases": 50},
    {"name": "Google UAC", "spend": 6000, "installs": 1500, "purchases": 100},
]

TARGET_CPA = 80
MIN_PURCHASES = 30

for campaign in campaigns:
    spend = campaign["spend"]
    purchases = campaign["purchases"]

    # Calculate CPA safely
    if purchases == 0:
        cpa = None
    else:
        cpa = spend / purchases

    # Apply our decision rules
    if purchases < MIN_PURCHASES:
        decision = "INVESTIGATE"
        reason = "Insufficient purchase data"

    elif cpa <= TARGET_CPA * 0.80:
        decision = "SCALE_CANDIDATE"
        reason = "CPA is at least 20% below target"

    elif cpa > TARGET_CPA * 1.50:
        decision = "REDUCE_CANDIDATE"
        reason = "CPA is more than 50% above target"

    else:
        decision = "INVESTIGATE"
        reason = "Performance needs further analysis"

    # Display the result
    print("-" * 45)
    print("Campaign:", campaign["name"])
    print("CPA:", f"₹{cpa:.2f}" if cpa is not None else "N/A")
    print("Target CPA:", f"₹{TARGET_CPA}")
    print("Decision:", decision)
    print("Reason:", reason)

print("-" * 45)
print("Decision engine completed.")
