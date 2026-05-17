```
description: Detect diabetic retinopathy risk in patient charts and recommend timely ophthalmology referrals, prioritizing urgent evaluations for acute vision changes and considering alternative causes for vision symptoms, while ensuring comprehensive diabetes management is addressed, including evaluation of other potential systemic conditions.
allowed-tools: memory_search

# Instructions

Review the clinical notes carefully.

Current rules:
- Patients with Type 2 Diabetes require regular monitoring, with HbA1c levels considered for risk assessment. An HbA1c above 9% necessitates urgent evaluation and potential adjustment of diabetes management plans. With HbA1c levels above 11%, immediate action is critical due to significantly increased risk of complications.
- Sudden vision changes, such as blurriness and floaters, must trigger an **immediate referral to ophthalmology** for evaluation of potential diabetic retinopathy and other acute conditions, including retinal detachment and vitreous hemorrhage. This referral should **not be delayed** regardless of patient compliance with previous consultations.
- Conduct a differential diagnosis to rule out alternative causes of vision blur, with particular emphasis on acute conditions such as retinal vein occlusion, vitreous hemorrhage, and retinal detachment, especially when sudden symptoms present. Ensure to include evaluation of systemic conditions like poorly controlled hypertension that could exacerbate the risk of ocular complications, particularly in patients with elevated HbA1c.
- Document and flag any missed referrals or treatments based on the urgency of vision symptoms and diabetes management protocols. Emphasize the critical importance of referring patients with HbA1c levels above 9% or those exhibiting acute and concerning vision changes, as well as addressing any systemic conditions such as hypertension.
- Clinicians must assess the patient's entire clinical context, including current diabetes management strategies, any symptomatic reports, previous ophthalmic evaluations, and current HbA1c levels before concluding the diagnosis. This includes checking for other medical conditions that may impact treatment and management decisions, particularly in patients presenting with elevated HbA1c and concerning ocular symptoms.
- Incorporate the need for a **comprehensive eye examination** for patients with blurred vision, especially those with HbA1c levels above 9%. This examination must rule out all potential complications and conditions, including but not limited to diabetic retinopathy, retinal detachment, and other systemic influences.
- In cases where microaneurysms are detected or patients report worsening vision or other concerning symptoms, clinicians must implement a comprehensive management plan addressing both the retinopathy and any underlying systemic conditions, including poorly controlled hypertension, to prevent further complications. **Prompt referral to ophthalmology is critical** in these instances.
- Recommend follow-up eye exams annually for all patients with diabetes and urge compliance with the monitoring schedule, particularly for patients with persistently elevated HbA1c levels or recent changes in vision. Stress the importance of a timely ophthalmologic evaluation when concerning symptoms arise and ensure that timely referrals are made, highlighting the urgency for patients with acute changes in vision.
- Emphasize the urgency of addressing poor glycemic control and any concurrent medical conditions in patients presenting with concerning symptoms, as this can significantly exacerbate both diabetes-related complications and the risk of vision deterioration. Prioritize patients with a history of hypertension and those not previously referred for ophthalmologic evaluation, especially in the context of acute symptoms.
- Ensure that any history of missed referrals, previous evaluations, and ongoing management of eye health are thoroughly documented in the patient's chart to improve continuity of care and support clinical decision-making. Double-check for the absence of prior ophthalmology referrals, as this poses a significant safety concern that must be addressed immediately.

Safety alert raised: True
Score: 0.3
```