"""Demo dataset for the dashboard, history, and coaching pages.

The three featured demo calls (app.sample_data) plus fifteen more, spread over
three weeks and four agents. The mix is deliberate: Maya is a consistently
strong agent, Priya is solid, Chris books calls but skips value and objection
handling, and Jake rarely asks for the appointment. That gives the coaching
page recurring gaps to find.

All companies, people, addresses, phone numbers (555-01xx range), and emails
(example.com) are invented for demonstration purposes.
"""

from datetime import date

from app.sample_data import DEMO_CALLS
from app.schemas import BusinessType

MAYA_FURNACE = """\
Agent: Good morning, thank you for calling Summit Heating and Air, this is Maya. How can I help?
Customer: Hi, my name is Grace Holloway. Our furnace stopped working overnight and there's no heat in the house.
Agent: I'm sorry to hear that, Grace. Let's get you warm again. When did you first notice it?
Customer: Around 5 this morning. It was 61 degrees inside when I woke up.
Agent: Is the furnace making any noise, and does the thermostat screen still turn on?
Customer: The thermostat is on, but the furnace just clicks and nothing happens.
Agent: Do you smell gas anywhere near the unit?
Customer: No, nothing like that.
Agent: Good, that's safe. How old is the furnace, roughly?
Customer: Maybe twelve years.
Agent: What's the address so I can confirm you're in our service area?
Customer: 305 Juniper Lane, Lakeview Springs.
Agent: Perfect, that's in our area. Do you own the home?
Customer: Yes.
Agent: What's the best number to reach you, and an email for the confirmation?
Customer: (512) 555-0152, and grace.holloway@example.com.
Agent: Thank you. Our technicians are licensed and insured, and all repairs come with a one-year warranty. I can send a technician today at 1 p.m. or 4 p.m. Which works better?
Customer: 1 p.m., please.
Agent: You're all set for today at 1 p.m. You'll get a text confirmation shortly, and the technician will call you 30 minutes before arriving. Anything else I can help with?
Customer: No, thank you so much.
Agent: You're welcome, Grace. Stay warm, and thanks for calling Summit Heating and Air.
"""

JAKE_GUTTERS = """\
Agent: Summit Roofing.
Customer: Hi, this is Ben Carter. My gutters are overflowing every time it rains and water is pooling by the foundation.
Agent: Yeah, they're probably clogged.
Customer: Can you guys clean them out or do they need replacing?
Agent: Could be either one. Gotta see them.
Customer: Okay, what would that cost?
Agent: Depends on the size of the house. No idea without seeing it.
Customer: Alright. Can someone take a look?
Agent: You can give us a call back next week, the schedule's full right now.
Customer: Fine. My number is (512) 555-0164 if that helps.
Agent: Okay, thanks.
"""

CHRIS_WATER_HEATER = """\
Agent: Thanks for calling Summit Plumbing, this is Chris. How can I help you?
Customer: Hi, my name is Rosa Delgado. Our water heater is making a popping noise and the water isn't getting very hot anymore.
Agent: Okay. How old is the water heater?
Customer: About ten years, I think.
Agent: Is it gas or electric?
Customer: Gas.
Agent: Any water around the base of the tank?
Customer: A little bit, yeah.
Agent: Got it. Can I get the address and the best phone number?
Customer: 74 Cedar Point Road, Lakeview Springs. My number is (512) 555-0187.
Agent: And do you own the home?
Customer: Yes. Honestly, I'm worried a new water heater is going to be really expensive.
Agent: It can be, it depends on the model. We have an opening Thursday at 9 a.m. if you want to schedule a technician.
Customer: I need to think about it. I'll let you know.
Agent: Okay, thanks for calling.
"""

PRIYA_GARAGE = """\
Agent: Good afternoon, Summit Home Services, this is Priya. How can I help?
Customer: Hi, I'm Marcus Webb. My garage door won't close all the way. It stops about a foot from the ground and goes back up.
Agent: I'm sorry to hear that, that sounds frustrating. When did it start doing that?
Customer: Two days ago.
Agent: Is anything blocking the sensors near the bottom of the track?
Customer: I checked, nothing's in the way.
Agent: Have you noticed any grinding noise or a broken spring?
Customer: No, it sounds normal.
Agent: What's the address there?
Customer: 19 Aspen Way, Lakeview Springs.
Agent: Great, we service that area. Is the house secure right now, or is the garage stuck open?
Customer: It's stuck open, so I'd like it fixed soon.
Agent: Understood. Our technicians are licensed and insured, and we give a written estimate upfront. I can have someone out tomorrow at 10 a.m. Does that work for you?
Customer: Yes, that works.
Agent: I've booked you for tomorrow at 10 a.m. What's the best phone number and email for the confirmation?
Customer: (512) 555-0135, marcus.webb@example.com.
Agent: Thank you, Marcus. You'll get a confirmation email shortly. Have a great day!
"""

JAKE_THERMOSTAT = """\
Agent: Heating and Air.
Customer: Hi. I was just wondering if you install smart thermostats.
Agent: Yeah, we do that.
Customer: What does that usually run?
Agent: Um, depends on the thermostat. Couple hundred, maybe.
Customer: Okay. I'm just getting ideas for now, no rush.
Agent: Okay. Whatever works for you.
Customer: I'll think about it. Thanks.
Agent: Yep.
"""

CHRIS_ROOF_REPLACEMENT = """\
Agent: Thank you for calling Summit Roofing, this is Chris.
Customer: Hi. I'm collecting quotes for a roof replacement. The roof is about twenty-five years old and the shingles are curling.
Agent: Okay. How big is the house, roughly?
Customer: About two thousand square feet, single story.
Agent: Any water getting in right now?
Customer: No, nothing like that. We're planning to do it in the spring.
Agent: Got it. Roughly how much did the other quotes come in at?
Customer: Around fourteen thousand. Honestly, I'm looking for whoever is cheaper.
Agent: Okay. We'd have to see it to give you a price.
Customer: Sure. I'd rather not give out my details yet. Do you have a website?
Agent: Yes, it's on our ads. Thanks for calling.
"""

MAYA_BURST_PIPE = """\
Agent: Thank you for calling Summit Plumbing, this is Maya. How can I help?
Customer: Hi, my name is Owen Fletcher. A pipe burst in our basement and there's water everywhere!
Agent: I'm so sorry, Owen, that sounds stressful. Let's get this handled right away. Have you been able to shut off the main water valve?
Customer: Yes, my neighbor helped me shut it off a few minutes ago.
Agent: Good, that stops more water coming in. Is the water near any outlets or the breaker panel?
Customer: No, it's on the other side of the basement.
Agent: How much water is on the floor, roughly?
Customer: Maybe an inch across half the basement.
Agent: What's the address? I want to confirm we can get there quickly.
Customer: 512 Harbor View Drive, Lakeview Springs.
Agent: That's in our service area. Are you the homeowner?
Customer: Yes, I own it.
Agent: What's the best number to reach you, and your email?
Customer: (512) 555-0118, owen.fletcher@example.com.
Agent: Thank you. We offer same-day emergency service, our plumbers are licensed and insured, and we can document the damage for your insurance claim. I can have a plumber there today by 11 a.m.
Customer: Please do.
Agent: You're all set. A plumber is on the way and will arrive today by 11 a.m. You'll get a text with their name and a tracking link. Anything else?
Customer: No, thank you.
Agent: You're welcome, Owen. Thank you for calling Summit Plumbing.
"""

PRIYA_AC_ELDERLY = """\
Agent: Good afternoon, Summit Heating and Air, this is Priya. How can I help?
Customer: Hi, this is Helen Brooks. Our AC is blowing warm air and it's 90 degrees outside. My mother lives with us and she's elderly.
Agent: I'm sorry to hear that, Helen. Let's get you cooled down quickly. When did the AC stop cooling?
Customer: Last night.
Agent: Is the outdoor unit running at all, and have you checked the breaker?
Customer: The outside fan isn't spinning. The breaker looks fine.
Agent: How old is the system?
Customer: Around eight years.
Agent: What's the service address?
Customer: 61 Birchwood Court, Lakeview Springs.
Agent: Great, we cover that area. Is your mother safe right now, or does anyone need to stay somewhere cooler?
Customer: She's okay for now with fans.
Agent: Good. Our technicians are certified and every repair has a warranty. I can get someone out today at 2 p.m. Does that work for you?
Customer: Yes, please.
Agent: I've booked you for today at 2 p.m. Can I confirm the best phone number for the technician?
Customer: (512) 555-0129.
Agent: Thank you. The technician will call you 30 minutes before arriving. Thanks for calling, Helen.
"""

JAKE_DRAIN = """\
Agent: Summit Plumbing.
Customer: Hi, this is Karen Mills. I've called twice about my kitchen drain and nobody called me back. It's still clogged and the water won't go down.
Agent: Okay, gimme a sec. Yeah, I don't see anything.
Customer: This is really frustrating. Can someone come out this week?
Agent: I dunno, the techs are booked up. You can try again tomorrow morning.
Customer: That's ridiculous. My number is (512) 555-0193.
Agent: Okay. I'll pass it along.
"""

CHRIS_FURNACE_NOISE = """\
Agent: Summit Heating and Air, this is Chris.
Customer: Hi, my name is Daniel Ortiz. Our furnace has started making a loud banging noise when it kicks on.
Agent: How long has it been doing that?
Customer: About a week, and it's getting worse.
Agent: Is the house still heating okay?
Customer: Yes, it still heats.
Agent: What's your address?
Customer: 230 Sycamore Street, Lakeview Springs.
Agent: And the best phone number?
Customer: (512) 555-0146.
Agent: We can send a technician Friday at 11 a.m. Does that work?
Customer: Yes, that's fine.
Agent: Okay, you're scheduled for Friday at 11 a.m. The tech will call you before arriving.
"""

MAYA_WIND_SHINGLES = """\
Agent: Thank you for calling Summit Roofing, this is Maya. How can I help you today?
Customer: Hi Maya, this is Paul Jensen. The wind storm yesterday blew some shingles off the back of our roof.
Agent: I'm sorry to hear that, Paul. Let's make sure it doesn't turn into a leak. Is any water coming inside right now?
Customer: Not that I've seen, but I'd like someone to look at it this week.
Agent: Roughly how many shingles are missing, and how old is the roof?
Customer: Maybe ten shingles. The roof is about nine years old.
Agent: Have you had any other damage on the property, like gutters or siding?
Customer: One gutter is hanging loose.
Agent: What's the property address? I'll confirm it's in our service area.
Customer: 47 Ridgecrest Drive, Lakeview Springs.
Agent: Perfect, we cover that area. Are you the homeowner, and what's the best number and email for you?
Customer: Yes, I own it. (512) 555-0172 and paul.jensen@example.com.
Agent: Thank you. The inspection is free, we're licensed and insured, and we can help with the insurance claim if the damage is covered. I have Thursday at 9 a.m. or 1 p.m. Which works better for you?
Customer: Thursday at 9.
Agent: You're all set for Thursday at 9 a.m. You'll get a confirmation text, and the inspector will call before arriving. Thanks for calling Summit Roofing, Paul!
"""

PRIYA_TOILET = """\
Agent: Good morning, Summit Plumbing, this is Priya. How can I help?
Customer: Hi, my name is Nina Patel. Our upstairs toilet keeps running after it flushes. It's nothing serious, just annoying.
Agent: I understand, and it can waste a lot of water. How long has it been running like that?
Customer: A couple of weeks.
Agent: Does it stop if you jiggle the handle, and is there any water on the floor?
Customer: Jiggling helps sometimes. The floor is dry.
Agent: What's the address there?
Customer: 16 Lantern Place, Lakeview Springs.
Agent: Great, that's in our service area. What's the best email or number to reach you?
Customer: nina.patel@example.com. I'd prefer email for now.
Agent: Of course. We offer free estimates, and most toilet repairs come with a one-year warranty. Would you like to book a visit this week?
Customer: Not yet, I'm checking our schedule. Can you email me some options?
Agent: Absolutely. I'll email you available times, and I'll follow up Friday at 10 a.m. if we haven't heard back.
Customer: Sounds good, thanks.
Agent: Thank you, Nina. Have a great day.
"""

JAKE_ROOF_LEAK = """\
Agent: Summit Roofing, Jake speaking.
Customer: Hi, my name is Sofia Ramirez. Water is coming through the ceiling in our living room after the rain this morning.
Agent: Okay. Gonna need someone to look at that.
Customer: Yes, that's why I'm calling. Can someone come out today?
Agent: Um, probably not today. Maybe later this week.
Customer: It's dripping onto the floor right now. What should I do?
Agent: Put a bucket under it, I guess.
Customer: Okay... my number is (512) 555-0157 and I'm at 802 Pecan Hollow Road.
Agent: Okay, someone will call you.
"""

CHRIS_DECK = """\
Agent: Thank you for calling Summit Home Services, this is Chris.
Customer: Hi, this is Laura Kim. A few boards on our back deck are rotting and one step feels loose.
Agent: How big is the deck?
Customer: About twelve by sixteen feet.
Agent: Is the loose step safe to use right now?
Customer: We're avoiding it for now.
Agent: What's the address and best phone number?
Customer: 140 Orchard Lane, Lakeview Springs, and (512) 555-0168. What would something like this cost? We're on a tight budget this year.
Agent: I understand. We can do a free estimate so you know the price before anything is done. Would you like to schedule the estimate?
Customer: I want to talk it over with my husband first.
Agent: Okay, give us a call back when you're ready. Thanks.
"""

MAYA_AC_REPLACEMENT = """\
Agent: Good afternoon, thank you for calling Summit Heating and Air, this is Maya.
Customer: Hi, my name is Victor Huang. Our AC is nineteen years old and the last tech said it needs replacing. I'm worried about the price.
Agent: I completely understand, Victor. A new system is a big decision. Is the AC still cooling for now?
Customer: It's cooling, but not well, and our power bills have gone way up.
Agent: How many square feet is the home, and are there any rooms that never get cool?
Customer: About eighteen hundred square feet. The upstairs bedrooms are always warm.
Agent: Have you had any repairs on it this year?
Customer: Two, which is why I'm thinking about replacing it.
Agent: That makes sense. What's the address there, and do you own the home?
Customer: 27 Magnolia Circle, Lakeview Springs, and yes, we own it.
Agent: Great, that's in our service area. Here's how we can help with cost: the in-home estimate is free with no obligation, we offer financing with low monthly payments, and new systems come with a ten-year warranty. A more efficient unit can also save you on those power bills.
Customer: Financing would help.
Agent: I can have a comfort advisor out Saturday at 10 a.m. or Monday at 4 p.m. Which works better for you?
Customer: Saturday works.
Agent: You're all set for Saturday at 10 a.m. What's the best phone number and email for the confirmation?
Customer: (512) 555-0183, victor.huang@example.com.
Agent: Thank you, Victor. You'll get a confirmation email shortly, and the advisor will call you before arriving. Have a great day!
"""


def _call(key, agent_name, business_type, call_date, transcript):
    return {
        "key": key,
        "agent_name": agent_name,
        "business_type": business_type,
        "call_date": call_date,
        "transcript": transcript,
    }


SEED_CALLS = [
    *DEMO_CALLS,
    _call("maya_furnace", "Maya Torres", BusinessType.HVAC, date(2026, 9, 22), MAYA_FURNACE),
    _call("jake_gutters", "Jake Miller", BusinessType.ROOFING, date(2026, 9, 23), JAKE_GUTTERS),
    _call("chris_water_heater", "Chris Novak", BusinessType.PLUMBING, date(2026, 9, 24), CHRIS_WATER_HEATER),
    _call("priya_garage", "Priya Shah", BusinessType.GENERIC, date(2026, 9, 25), PRIYA_GARAGE),
    _call("jake_thermostat", "Jake Miller", BusinessType.HVAC, date(2026, 9, 29), JAKE_THERMOSTAT),
    _call("chris_roof_replacement", "Chris Novak", BusinessType.ROOFING, date(2026, 9, 30), CHRIS_ROOF_REPLACEMENT),
    _call("maya_burst_pipe", "Maya Torres", BusinessType.PLUMBING, date(2026, 10, 2), MAYA_BURST_PIPE),
    _call("priya_ac_elderly", "Priya Shah", BusinessType.HVAC, date(2026, 10, 5), PRIYA_AC_ELDERLY),
    _call("jake_drain", "Jake Miller", BusinessType.PLUMBING, date(2026, 10, 6), JAKE_DRAIN),
    _call("chris_furnace_noise", "Chris Novak", BusinessType.HVAC, date(2026, 10, 7), CHRIS_FURNACE_NOISE),
    _call("maya_wind_shingles", "Maya Torres", BusinessType.ROOFING, date(2026, 10, 8), MAYA_WIND_SHINGLES),
    _call("priya_toilet", "Priya Shah", BusinessType.PLUMBING, date(2026, 10, 9), PRIYA_TOILET),
    _call("jake_roof_leak", "Jake Miller", BusinessType.ROOFING, date(2026, 10, 10), JAKE_ROOF_LEAK),
    _call("chris_deck", "Chris Novak", BusinessType.GENERIC, date(2026, 10, 12), CHRIS_DECK),
    _call("maya_ac_replacement", "Maya Torres", BusinessType.HVAC, date(2026, 10, 13), MAYA_AC_REPLACEMENT),
]
