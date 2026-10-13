"""Fictional demo transcripts.

All companies, people, addresses, phone numbers (555-01xx range), and emails
(example.com) are invented for demonstration purposes.
"""

from datetime import date

from app.schemas import BusinessType

ROOFING_STRONG = """\
Agent: Thank you for calling Summit Roofing, this is Maya. How can I help you today?
Customer: Hi Maya, my name is Dana Whitfield. We had that big hail storm last night and now there's water dripping through our bedroom ceiling.
Agent: I'm sorry to hear that, Dana. That sounds stressful, so let's get you taken care of. Is the water actively coming in right now?
Customer: Yes, it's still dripping. I put a bucket under it.
Agent: Good thinking. When did you first notice it, and is it just the one spot?
Customer: Around six this morning. Just the one spot, but the stain is getting bigger.
Agent: Is anyone in the home at risk, or is the water near any light fixtures?
Customer: No, it's away from the lights.
Agent: Do you know roughly how old the roof is, and have you had any repairs before?
Customer: It's about fifteen years old. No repairs that I know of.
Agent: Thanks. What's the address of the property so I can confirm we service your area?
Customer: 1420 Maple Ridge Drive in Lakeview Springs.
Agent: Great, Lakeview Springs is in our service area. And are you the homeowner?
Customer: Yes, we own the home.
Agent: Perfect. What's the best phone number to reach you?
Customer: (512) 555-0143.
Agent: And an email for your confirmation?
Customer: dana.whitfield@example.com
Agent: Thank you. Here's what we can do: we offer a free storm damage inspection, our inspectors are licensed and insured, and if there's hail damage we can help document it for your insurance claim. We can also put a temporary tarp on today to stop the leak.
Customer: That would be great. How soon can someone come out?
Agent: I can send a crew today at 3 p.m. for the tarp and inspection, or first thing tomorrow at 8 a.m. Which works better for you?
Customer: Today at 3 works.
Agent: You're all set. I've booked your inspection and emergency tarp for today at 3 p.m. You'll get a text confirmation in a few minutes, and the inspector will call you about 30 minutes before arriving. Is there anything else I can help with?
Customer: No, that's it. Thank you so much.
Agent: You're welcome, Dana. Thanks for calling Summit Roofing, and have a good rest of your day.
"""

HVAC_WEAK = """\
Agent: Summit Heating and Air.
Customer: Hi, yeah, my AC stopped cooling yesterday and it's like 88 degrees in the house. My name's Tom Reyes.
Agent: Okay. What kind of unit is it?
Customer: I'm not sure, it's whatever came with the house. It's blowing but the air is warm.
Agent: Yeah, could be a lot of things. Could be the capacitor, could be refrigerant.
Customer: How much does it usually cost to come out and look at it?
Agent: It depends on what's wrong. I dunno exactly, the tech would have to tell you.
Customer: Okay... is there any way someone could come out soon? We have a newborn at home.
Agent: We're pretty busy this week. You can call back tomorrow and check if something opens up.
Customer: Alright, I guess. My number is (512) 555-0178 if anyone can call me.
Agent: Okay. Thanks for calling.
"""

PLUMBING_PRICE_OBJECTION = """\
Agent: Good afternoon, Summit Plumbing, this is Priya. How can I help?
Customer: Hi, this is Linda Park. I've got a leaking pipe under my kitchen sink. It's a slow drip but it's getting worse.
Agent: I'm sorry to hear that, Linda. How long has it been leaking, and is there any water damage to the cabinet?
Customer: About a week. The cabinet floor is a little warped.
Agent: Is it coming from the supply line or the drain pipe, if you can tell?
Customer: I think the drain pipe. It drips when we run the dishwasher.
Agent: Have you been able to shut off the valve under the sink?
Customer: Yes, I turned it off for now, so we're managing.
Agent: Good, that will limit any damage. What's the address there?
Customer: 88 Willow Court, Lakeview Springs.
Agent: Great, we cover that area.
Customer: Honestly, I'm worried about the cost. The last plumber charged us a fortune.
Agent: I completely understand. The good news is the inspection is free and there's no obligation. The technician will give you a written estimate upfront before any work starts, and we offer financing on larger repairs. All our work also comes with a one-year warranty.
Customer: That helps. I still want to talk it over with my husband before booking anything, though.
Agent: Of course. Would it help if I held a free inspection slot for Wednesday at 2 p.m. while you two talk it over?
Customer: Let me check with him first.
Agent: No problem. What's the best number to reach you, and what's your email? I'll send our pricing information today.
Customer: It's (512) 555-0121, and my email is linda.park@example.com.
Agent: Thanks, Linda. You'll get an email from us today, and I'll call you tomorrow at 10 a.m. to see what works for you. Thanks for calling Summit Plumbing!
"""

DEMO_CALLS = [
    {
        "key": "roofing_strong",
        "label": "Roofing: storm leak, inspection booked (strong call)",
        "agent_name": "Maya Torres",
        "business_type": BusinessType.ROOFING,
        "call_date": date(2026, 9, 28),
        "transcript": ROOFING_STRONG,
    },
    {
        "key": "hvac_weak",
        "label": "HVAC: AC not cooling, no appointment requested (weak call)",
        "agent_name": "Jake Miller",
        "business_type": BusinessType.HVAC,
        "call_date": date(2026, 10, 1),
        "transcript": HVAC_WEAK,
    },
    {
        "key": "plumbing_objection",
        "label": "Plumbing: leaking pipe, price objection handled (callback set)",
        "agent_name": "Priya Shah",
        "business_type": BusinessType.PLUMBING,
        "call_date": date(2026, 10, 3),
        "transcript": PLUMBING_PRICE_OBJECTION,
    },
]
