# Lab 2 Step 1: Baseline (Model Without Tools)

## Budget Question (3 Runs)
Prompt: "I have GHS 1,200. I want 4 bags of rice at GHS 185 each and 3 gallons of oil at GHS 95 each. How much will I have left?"
Expected calculation: 1200 - (4 * 185 + 3 * 95) = 1200 - (740 + 285) = 1200 - 1025 = 175 GHS.

- **Run 1:** Calculated 4 × 185 = GHS 740, 3 × 95 = GHS 285, total spent = GHS 1,025, remaining = GHS 175 ("You will have GHS 175 left.") — **Arithmetic:** Correct
- **Run 2:** Calculated 4 × 185 = GHS 740, 3 × 95 = GHS 285, total spent = GHS 1,025, remaining = GHS 175 ("You will have GHS 175 left.") — **Arithmetic:** Correct
- **Run 3:** Calculated 4 × 185 = GHS 740, 3 × 95 = GHS 285, total spent = GHS 1,025, remaining = GHS 175 ("You will have GHS 175 left.") — **Arithmetic:** Correct

## Factual Questions (2 Runs)
1. **Prompt:** "What is the capital of the Bono East Region of Ghana?"
   - **Response:** "The capital of the Bono East Region of Ghana is Techiman."
   - **Accuracy & Confidence:** Correct; concise and direct with high confidence.

2. **Prompt:** "Who founded Makola Market in Accra?"
   - **Response:** Stated it was not founded by a single individual, crediting the Ga people in the late 19th century (circa 1870s–1890s) and listing historical/reference details.
   - **Accuracy & Confidence:** Partially plausible / unverified by live lookup; the model sounded very confident and authoritative with structured tables and cited book titles from memory even though no external source was retrieved during the run.