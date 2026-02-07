# Test MCP Prompts for Concord

Use these prompts in the Claude Mac App to verify the Concord MCP server is working correctly.

---

## Test 1: List Available CPGs

```
List all available clinical practice guidelines.
```

**Expected:** You should see a list of ~19 CPGs including cholesterol, diabetes screening, hypertension screening, etc.

---

## Test 2: Get CPG Details

```
Get detailed information about the "uspstf_statinuse" clinical practice guideline.
```

**Expected:** Detailed info including title, publisher, variables, assessments, and recommendations.

---

## Test 3: Create Patient and Evaluate (Complete Data)

```
Create a health context for a 55-year-old male patient with the following data:
- Age: 55
- Gender: Male (use code: http://snomed.info/sct|248153007)
- Ethnicity: White (use code: urn:oid:2.16.840.1.113883.6.238|2106-3)
- LDL cholesterol: 145 mg/dL
- HDL cholesterol: 38 mg/dL
- Total cholesterol: 220 mg/dL
- Triglycerides: 185 mg/dL
- Systolic blood pressure: 142 (as tuple with diastolic, e.g., (142, 90))
- Has diabetes: yes (value: 1 or true)
- Has hypertension: yes (value: 1 or true)
- Is a current smoker: yes (value: 1 or true)
- On hypertension medication: no (value: 0 or false)
- On statin medication: no (value: 0 or false)
- On non-statin cholesterol medication: no (value: 0 or false)

Then evaluate this patient against the uspstf_statinuse guideline and show me the recommendations.
```

**Expected:** You should see:
- Eligibility result (eligible/not eligible)
- Assessment results including **ASCVD 10-year risk score** (should be ~30% for this patient)
- Specific statin recommendations with USPSTF Grade B

---

## Test 3b: Missing Data Handling (CRITICAL TEST)

This test verifies that Claude does NOT fabricate missing patient data.

```
Create a health context for a patient with ONLY the following data:
- Age: 55
- Gender: Male
- LDL cholesterol: 145 mg/dL
- HDL cholesterol: 38 mg/dL
- Systolic blood pressure: 142
- Has diabetes: yes
- Is a current smoker: yes

Then evaluate this patient against the uspstf_statinuse guideline.
```

**Expected Behavior (CORRECT):**

Claude should:
1. Create the health context with ONLY the data provided
2. Call evaluate_patient
3. See that data is missing in the response
4. **ASK the user for the missing data** - something like:
   > "I need additional information to complete your cardiovascular risk assessment:
   >
   > 1. **Total Cholesterol (Chol)**: What is your total cholesterol level?
   > 2. **Triglycerides**: What is your triglyceride level?
   > 3. **Ethnicity**: What is your ethnicity?
   > 4. **Hypertension Medication**: Are you taking any medication for high blood pressure?
   > 5. **Statin Medication**: Are you currently taking any statin medications?
   > 6. **Non-statin cholesterol medication**: Are you on any other cholesterol-lowering medications?
   >
   > Please provide these values so I can complete the evaluation."

**Wrong Behavior (INCORRECT):**

Claude should NOT:
- Fill in missing values with assumed/typical values
- Estimate total cholesterol as 220 because "LDL is 145"
- Add ethnicity as "White" without asking
- Assume medication status as "no" without asking
- Proceed with partial results without asking for missing data

---

## Test 4: Get Prioritized Recommendations

```
For the patient I just created, get the prioritized recommendations ranked by evidence strength.
```

**Expected:** Recommendations sorted by Class of Recommendation (I, IIa, IIb, III) and Level of Evidence.

---

## Test 5: Explain a Recommendation

```
Explain why the statin recommendation applies to this patient. Show the assessment chain and evidence.
```

**Expected:** Detailed explanation with assessment values that led to the recommendation.

---

## Test 6: Evaluate Against All CPGs

```
Evaluate the current patient against ALL available clinical practice guidelines and summarize which ones apply.
```

**Expected:** A summary showing which CPGs the patient is eligible for and key recommendations from each.

---

## Test 7: Get Missing Data

```
What health data is missing to complete the evaluation for this patient?
```

**Expected:** A list of variables that are missing or need attestation.

---

## Test 8: Submit Attestation

```
The patient confirms they have no family history of heart disease and they exercise regularly. Submit this information.
```

**Expected:** Confirmation that the attestation was recorded and re-evaluation if applicable.

---

## Test 9: Interactive Data Collection

This tests the full workflow where Claude asks for missing data and user provides it.

**Step 1 - Start with incomplete data:**
```
I'm a 55-year-old male. My LDL is 145 and HDL is 38. I have diabetes and I smoke. Can you evaluate my cardiovascular risk?
```

**Expected Step 1:** Claude should ask for missing information (total cholesterol, triglycerides, blood pressure, ethnicity, medication status).

**Step 2 - Provide some missing data:**
```
My total cholesterol is 220, triglycerides are 185, and blood pressure is 142/90.
```

**Expected Step 2:** Claude should acknowledge the new data and ask for remaining missing information (ethnicity, medication status).

**Step 3 - Complete the data:**
```
I'm White, I have hypertension but I'm not on any medications for it. I don't take any statins or other cholesterol medications.
```

**Expected Step 3:** Claude should now have complete data and provide the full ASCVD risk evaluation with recommendations.

---

## Test 10: Get Evaluation Metadata (Reproducibility)

This tests the cryptographic reproducibility features.

```
For the patient I just evaluated, show me the evaluation metadata including the input and output hashes for reproducibility verification.
```

**Expected:** Response should include:
- CPG version
- Input data hash (SHA-256)
- Output hash (SHA-256)
- Evaluation timestamp
- A note about reproducibility guarantee

---

## Test 11: Verify Reproducibility

```
Verify that my previous cardiovascular risk evaluation is reproducible. Use the hashes from the metadata.
```

**Expected:** Response should show:
- Status: "VERIFIED"
- Verified: true
- Confirmation that input and output hashes match
- Note about Concord's deterministic guarantee

---

## Test 12: Evaluate Multiple CPGs in Parallel

```
Evaluate my current patient against these CPGs in parallel:
- uspstf_statinuse
- cholesterol
- uspstf_hypertension_screening

Show me the combined results and any conflicts detected.
```

**Expected:**
- Multiple CPGs evaluated
- Elapsed time in milliseconds (should be fast)
- Combined recommendations from all CPGs
- Any conflicts between recommendations

---

## Test 13: Performance Demonstration

```
How many CPGs did you just evaluate and how long did it take? Compare this to how long it would take an LLM to reason through the same guidelines.
```

**Expected:** Claude should note:
- Number of CPGs evaluated
- Total elapsed time (typically <5ms)
- This is 100-1000x faster than LLM reasoning
- This is deterministic (same input = same output)

---

## How to Verify Responses are from Concord

Look for these indicators in Claude's responses:

1. **Tool usage indicators** - Claude should show it's using tools like `list_cpgs`, `evaluate_patient`, etc.

2. **Specific CPG data** - Real CPG identifiers like:
   - `uspstf_statinuse`
   - `cholesterol`
   - `uspstf_diabetes_screening`
   - `uspstf_hypertension_screening`

3. **Clinical terminology** - Terms like:
   - "Class of Recommendation"
   - "Level of Evidence"
   - "USPSTF Grade"
   - "Eligibility criteria"
   - "Sufficiency check"

4. **Variable IDs** - Specific variable names from the CPGs:
   - `LDL`, `HDL`, `Chol` (lipids)
   - `bloodpressure`
   - `is_smoker`, `diabetesMellitus`
   - `Age`, `Gender`

5. **Structured results** - Clear phases:
   - Eligibility evaluation
   - Sufficiency check
   - Assessment results
   - Recommendations with evidence grades

---

## Troubleshooting

If Concord is NOT connected, Claude will:
- Say "I don't have access to clinical practice guidelines"
- Try to answer from general medical knowledge without using tools
- Not show any tool usage indicators

### Check MCP Server Status

In Claude Mac App, you can check connected MCP servers in the settings or by asking:

```
What MCP tools do you have available?
```

If Concord is connected, you should see tools like `list_cpgs`, `evaluate_patient`, `get_recommendations`, etc.

### If Claude Fabricates Data

If Claude still fills in missing data on its own:
1. Try accessing the `concord://guidelines` resource first
2. Or use the `concord_guidelines` prompt to load the guidelines
3. Report this as a bug - the MCP server should be preventing this behavior

### Check Server Logs

Run the server manually to see logs:
```bash
cd /path/to/concordcore
./run_mcp_server.sh
```

Watch for errors or warnings about data handling.
