"""Trade catalogue, sample rubric scores and sample job listings.

Rubric base scores and listings are SAMPLE data used by the mock providers.
"""
from __future__ import annotations

LANGS = ("en", "ta", "hi")
LANG_NAMES = {"en": "English", "ta": "Tamil", "hi": "Hindi"}

TRADE_ORDER = [
    "electrical", "tailoring", "solar",
    "plumbing", "hvac", "automobile",
    "pottery", "weaving", "carpentry",
    "masonry", "welding", "painting",
]

SECTOR_ORDER = ["technical", "crafts", "construction"]

SECTORS: dict[str, dict] = {
    "technical": {
        "id": "technical",
        "name": "Technical & Engineering Trades (Technicians)",
        "short": "Tech & Repairs 🛠️",
        "menu": {"en": "Tech & Repairs 🛠️", "ta": "தொழில்நுட்பம் & பழுது 🛠️", "hi": "तकनीकी व मरम्मत 🛠️"},
        "trades": ["electrical", "plumbing", "hvac", "automobile", "solar"],
    },
    "crafts": {
        "id": "crafts",
        "name": "Creative & Craft Sector (Artisans)",
        "short": "Crafts & Arts 🎨",
        "menu": {"en": "Crafts & Arts 🎨", "ta": "கைவினை & கலை 🎨", "hi": "शिल्प व हस्तकला 🎨"},
        "trades": ["tailoring", "pottery", "weaving", "carpentry"],
    },
    "construction": {
        "id": "construction",
        "name": "Construction & Infrastructure",
        "short": "Construction 🏗️",
        "menu": {"en": "Construction 🏗️", "ta": "கட்டுமானம் 🏗️", "hi": "भवन निर्माण 🏗️"},
        "trades": ["masonry", "welding", "painting"],
    },
}

TRADES: dict[str, dict] = {
    # ⚡ Technical & Engineering Trades
    "electrical": {
        "id": "electrical",
        "sector": "technical",
        "name": "Electrical Installation (House wiring, appliance repair, inverter setups)",
        "short": "Electrical Installation",
        "menu": {"en": "Electrical Installation", "ta": "மின் வயரிங்", "hi": "इलेक्ट्रिकल वायरिंग"},
        "sample_learner": "Karthik M.",
        "sample_mentor": "S. Karuppasamy",
        "sample_hours": 12,
        "level": 3,
        "tags": ["Domestic wiring", "Relay control", "Safe isolation"],
        "rubric": [
            ("Safe isolation before work (MCB off, insulated tools)", 95, None),
            ("Conductor routing and ferrule use", 88, None),
            ("Terminal tightness and strip length", 82, None),
            ("Continuity test performed", 90, None),
            ("Dressing and labelling of cables", 74, "Add cable labels so repairs are easier."),
        ],
        "viva": {
            "question": {
                "en": "A customer says their 16A MCB trips immediately when the geyser is turned on, but lights stay on. What 2 tests will you do with your multimeter before touching the wiring?",
                "ta": "வாடிக்கையாளர் கீசரை இயக்கும்போது 16A MCB உடனே ட்ரிப் ஆகிறது. வயரிங்கை தொடும் முன் மல்டிமீட்டர் மூலம் நீங்கள் செய்யும் 2 சோதனைகள் என்ன?",
                "hi": "गीजर चालू करते ही 16A MCB तुरंत ट्रिप हो जाता है। वायरिंग छूने से पहले मल्टीमीटर से आप कौन सी 2 जाँच करेंगे?",
            },
            "keywords": ["multimeter", "continuity", "element", "coil", "earth", "leakage", "insulation", "मल्टीमीटर", "कंटिन्यूटी", "எர்த்", "காயில்"],
            "say": {
                "en": "First I isolate the main switch, then test the geyser heating element continuity and check phase-to-earth for coil insulation leakage.",
                "ta": "முதலில் மெயின் ஸ்விட்ச்சை அணைப்பேன். பிறகு கீசர் காயிலின் கன்டினியூட்டி மற்றும் எர்த் லீக்கேஜை மல்டிமீட்டரில் சரிபார்ப்பேன்.",
                "hi": "पहले मेन स्विच बंद करके गीजर के हीटिंग एलिमेंट का कंटिन्यूटी और फेज-टू-अर्थ लीकेज मल्टीमीटर से नापेंगे।",
            },
        },
        "say": {
            "en": "This student wired the relay cleanly in 10 minutes.",
            "ta": "இந்த மாணவர் ரிலேவை பத்து நிமிடங்களில் நேர்த்தியாக வயரிங் செய்தார்.",
            "hi": "इस छात्र ने दस मिनट में रिले की वायरिंग साफ़-सुथरी की।",
        },
    },
    "plumbing": {
        "id": "plumbing",
        "sector": "technical",
        "name": "Plumbing & Sanitation (Pipe threading, leak diagnostics, fixture installation)",
        "short": "Plumbing & Sanitation",
        "menu": {"en": "Plumbing & Sanitation", "ta": "குழாய் & சுகாதாரம்", "hi": "प्लंबिंग व सेनेटरी"},
        "sample_learner": "Saravanan P.",
        "sample_mentor": "M. Thangavel",
        "sample_hours": 24,
        "level": 3,
        "tags": ["Pipe threading", "Leak diagnostics", "Fixture installation"],
        "rubric": [
            ("Pipe cutting and de-burring accuracy", 92, None),
            ("Thread seal tape application and tightening", 88, None),
            ("Pressure test and leak diagnosis", 85, None),
            ("Waste water trap slope alignment", 80, None),
            ("Worksite cleanup and seal curing check", 75, "Allow adequate curing time before applying full line pressure."),
        ],
        "viva": {
            "question": {
                "en": "You joined a 1-inch suction line with a PVC union, but the monoblock pump keeps losing prime and pulls air bubbles. Where is the air entering and what fix will you do?",
                "ta": "1 இன்ச் உறிஞ்சும் குழாயில் மோனோபிளாக் பம்ப் ஏர் லாக் ஆகிறது. காற்று எங்கு கசிகிறது, அதை எப்படி சரிசெய்வீர்கள்?",
                "hi": "1 इंच सक्शन पाइप जोड़ने के बाद भी मोटर में बार-बार एयर लॉक हो रहा है। लीकेज कहाँ है और आप इसे कैसे ठीक करेंगे?",
            },
            "keywords": ["union", "o-ring", "teflon", "foot valve", "suction", "gasket", "टेफ्लॉन", "यूनियन", "டெஃப்லான்", "ஓ-ரிங்"],
            "say": {
                "en": "The air is entering from the union O-ring or foot valve threads. I will re-wrap Teflon tape, check the rubber gasket, and test under foot-valve pressure.",
                "ta": "யூனியன் ஓ-ரிங் அல்லது ஃபுட் வால்வு திரெட்டில் காற்று நுழைகிறது. டெஃப்லான் டேப் போட்டு கேஸ்கெட்டை இறுக்குவேன்.",
                "hi": "यूनियन के ओ-रिंग या फुट वाल्व के थ्रेड से हवा आ रही है। टेफ्लॉन टेप लगाकर रबर गैसकेट चेक करेंगे।",
            },
        },
        "say": {
            "en": "The air is entering from the union O-ring or foot valve threads. I will re-wrap Teflon tape, check the rubber gasket, and test under foot-valve pressure.",
            "ta": "யூனியன் ஓ-ரிங் அல்லது ஃபுட் வால்வு திரெட்டில் காற்று நுழைகிறது. டெஃப்லான் டேப் போட்டு கேஸ்கெட்டை இறுக்குவேன்.",
            "hi": "यूनियन के ओ-रिंग या फुट वाल्व के थ्रेड से हवा आ रही है। टेफ्लॉन टेप लगाकर रबर गैसकेट चेक करेंगे।",
        },
    },
    "hvac": {
        "id": "hvac",
        "sector": "technical",
        "name": "HVAC / AC Technician (Gas charging, compressor servicing, ducting)",
        "short": "HVAC / AC Technician",
        "menu": {"en": "HVAC / AC Technician", "ta": "ஏசி & குளிர்பதனம்", "hi": "एसी व रेफ्रिजरेशन"},
        "sample_learner": "Dinesh Kumar K.",
        "sample_mentor": "G. Venkatesh",
        "sample_hours": 30,
        "level": 4,
        "tags": ["Gas charging", "Compressor servicing", "Flaring and brazing"],
        "rubric": [
            ("Copper tube flaring and swaging precision", 90, None),
            ("System vacuuming down to required microns", 86, None),
            ("Refrigerant weight charging accuracy", 89, None),
            ("Electrical terminal safety and capacitor check", 84, None),
            ("Airflow temperature delta verification", 78, "Check suction pressure after 15 minutes of continuous running."),
        ],
        "viva": {
            "question": {
                "en": "A split AC indoor unit runs but the suction line freezes with white frost within 10 minutes. What does this frost indicate and what are your next steps?",
                "ta": "ஸ்பிளிட் ஏசி இயங்கும்போது 10 நிமிடத்தில் சக்ஷன் பைப் பனிக்கட்டியாக நிறைகிறது. இதற்கு என்ன காரணம்?",
                "hi": "स्प्लिट एसी चलने के 10 मिनट में सक्शन पाइप पर बर्फ जमने लगती है। इसका क्या कारण है?",
            },
            "keywords": ["frost", "suction", "refrigerant", "leak", "flare", "pressure", "बर्फ", "गैस", "பிரஷர்", "ஃப்ளேர்"],
            "say": {
                "en": "Frost on suction pipe means low refrigerant charge from a joint flare leak or a choked indoor filter blower. I will check standing pressure and soap bubble test the flares.",
                "ta": "கேஸ் கசிவு அல்லது இன்டோர் ஃபில்டர் அடைப்பு ஏற்பட்டுள்ளது. சோப் நுரை கொண்டு ஃப்ளேர் இணைப்புகளை பரிசோதித்து கேஸ் பிரஷர் பார்ப்பேன்.",
                "hi": "यह गैस कम होने या इंडोर कॉइल चोक होने का संकेत है। फ्लेयर नट पर साबुन का झाग लगाकर लीकेज चेक करेंगे।",
            },
        },
        "say": {
            "en": "Frost on suction pipe means low refrigerant charge from a joint flare leak or a choked indoor filter blower. I will check standing pressure and soap bubble test the flares.",
            "ta": "கேஸ் கசிவு அல்லது இன்டோர் ஃபில்டர் அடைப்பு ஏற்பட்டுள்ளது. சோப் நுரை கொண்டு ஃப்ளேர் இணைப்புகளை பரிசோதித்து கேஸ் பிரஷர் பார்ப்பேன்.",
            "hi": "यह गैस कम होने या इंडोर कॉइल चोक होने का संकेत है। फ्लेयर नट पर साबुन का झाग लगाकर लीकेज चेक करेंगे।",
        },
    },
    "automobile": {
        "id": "automobile",
        "sector": "technical",
        "name": "Automobile Repair (Two-wheeler servicing, engine tuning, wiring)",
        "short": "Automobile Repair",
        "menu": {"en": "Automobile Repair", "ta": "வாகன பழுதுபார்ப்பு", "hi": "ऑटोमोबाइल रिपेयर"},
        "sample_learner": "Praveen Raj",
        "sample_mentor": "K. Munusamy",
        "sample_hours": 35,
        "level": 3,
        "tags": ["Two-wheeler service", "Engine tuning", "Harness wiring"],
        "rubric": [
            ("Spark plug gap check and cleaning", 94, None),
            ("Carburetor/injector throttle adjustment", 86, None),
            ("Brake pad inspection and shoe clearance", 90, None),
            ("Battery voltage and charging circuit test", 85, None),
            ("Chain tensioning and lubrication", 76, "Keep recommended chain slack of 25mm to avoid bearing wear."),
        ],
        "viva": {
            "question": {
                "en": "A 125cc bike engine cranks with the self-starter but does not fire. Fuel is reaching the carburettor. What 2 ignition and spark checks will you do?",
                "ta": "பைக் செல்ஃப் ஸ்டார்ட் ஆகிறது ஆனால் என்ஜின் ஸ்டார்ட் ஆகவில்லை. பெட்ரோல் வருகிறது. நீங்கள் என்ன பரிசோதிப்பீர்கள்?",
                "hi": "बाइक का सेल्फ घूम रहा है लेकिन इंजन स्टार्ट नहीं हो रहा। पेट्रोल आ रहा है। आप करंट की क्या जाँच करेंगे?",
            },
            "keywords": ["spark", "plug", "coil", "gap", "carbon", "current", "स्पार्क", "प्लग", "கரண்ட்", "ஸ்பார்க்"],
            "say": {
                "en": "I will pull the spark plug cap to check high tension coil arc against the engine block, and inspect the plug tip gap and carbon.",
                "ta": "ஸ்பார்க் பிளக் கழற்றி என்ஜின் பாடியில் வைத்து ப்ளூ ஸ்பார்க் வருகிறதா மற்றும் கேப் சரியாக உள்ளதா என்று பார்ப்பேன்.",
                "hi": "स्पार्क प्लग खोलकर इंजन बॉडी पर नीला करंट चेक करेंगे और प्लग का गैप व कार्बन साफ करेंगे।",
            },
        },
        "say": {
            "en": "I will pull the spark plug cap to check high tension coil arc against the engine block, and inspect the plug tip gap and carbon.",
            "ta": "ஸ்பார்க் பிளக் கழற்றி என்ஜின் பாடியில் வைத்து ப்ளூ ஸ்பார்க் வருகிறதா மற்றும் கேப் சரியாக உள்ளதா என்று பார்ப்பேன்.",
            "hi": "स्पार्क प्लग खोलकर इंजन बॉडी पर नीला करंट चेक करेंगे और प्लग का गैप व कार्बन साफ करेंगे।",
        },
    },
    "solar": {
        "id": "solar",
        "sector": "technical",
        "name": "Solar Installation (Panel mounting, controller, DC wiring)",
        "short": "Solar Installation",
        "menu": {"en": "Solar Installation", "ta": "சோலார் பொருத்துதல்", "hi": "सोलर इंस्टॉलेशन"},
        "sample_learner": "Vignesh S.",
        "sample_mentor": "R. Durai",
        "sample_hours": 16,
        "level": 3,
        "tags": ["Solar PV basics", "Panel mounting", "DC wiring safety"],
        "rubric": [
            ("Panel tilt and shade check", 88, None),
            ("Mounting bracket tightness", 92, None),
            ("DC polarity and connector seating", 85, None),
            ("Charge controller connection order", 80, None),
            ("Earthing and safety awareness", 72, "Revise the earthing steps with your mentor."),
        ],
        "viva": {
            "question": {
                "en": "A rooftop solar array shows normal open circuit voltage (Voc), but current drops to near zero under load. What wiring or component is faulty?",
                "ta": "சோலார் பேனல் வோல்டேஜ் சரியாக உள்ளது, ஆனால் லோட் கொடுக்கும்போது கரண்ட் சுழியாகிறது. என்ன காரணம்?",
                "hi": "सोलर पैनल का वोल्टेज सही है लेकिन लोड देते ही करंट जीरो हो जाता है। कहाँ खराबी है?",
            },
            "keywords": ["mc4", "connector", "diode", "junction", "crimp", "loose", "डायोड", "कलेक्टर", "டயோட்", "கனெக்டர்"],
            "say": {
                "en": "This indicates a high-resistance loose crimp on an MC4 connector or a burnt bypass diode inside the module junction box.",
                "ta": "MC4 கனெக்டரில் லூஸ் காண்டாக்ட் அல்லது ஜங்ஷன் பாக்ஸில் பைபாஸ் டயோட் பழுதாகியுள்ளது. அதை சோதித்து மாற்றுவேன்.",
                "hi": "यह MC4 कनेक्टर के ढीले क्रिम्पिंग या जंक्शन बॉक्स के बाईपास डायोड के खराब होने का कारण है।",
            },
        },
        "say": {
            "en": "This indicates a high-resistance loose crimp on an MC4 connector or a burnt bypass diode inside the module junction box.",
            "ta": "MC4 கனெக்டரில் லூஸ் காண்டாக்ட் அல்லது ஜங்ஷன் பாக்ஸில் பைபாஸ் டயோட் பழுதாகியுள்ளது. அதை சோதித்து மாற்றுவேன்.",
            "hi": "यह MC4 कनेक्टर के ढीले क्रिम्पिंग या जंक्शन बॉक्स के बाईपास डायोड के खराब होने का कारण है।",
        },
    },

    # 🧵 Creative & Craft Sector
    "tailoring": {
        "id": "tailoring",
        "sector": "crafts",
        "name": "Tailoring & Embroidery (Blouse stitching, alterations, zari work)",
        "short": "Tailoring & Embroidery",
        "menu": {"en": "Tailoring & Embroidery", "ta": "தையல் & எம்பிராய்டரி", "hi": "सिलाई व कढ़ाई"},
        "sample_learner": "Anitha R.",
        "sample_mentor": "Lakshmi Ammal",
        "sample_hours": 20,
        "level": 3,
        "tags": ["Garment stitching", "Seam finishing", "Measurement"],
        "rubric": [
            ("Measurement and marking accuracy", 90, None),
            ("Straight seams and even stitch length", 86, None),
            ("Seam finishing, no loose threads", 78, "Trim loose threads at seam ends."),
            ("Machine safety and posture", 94, None),
            ("Overall fit and neatness", 88, None),
        ],
        "viva": {
            "question": {
                "en": "When stitching a silk blouse on the sewing machine, the bottom thread is bunching up in bird's nests and puckering the fabric. How will you adjust the tensions?",
                "ta": "பட்டு ரவிக்கை தைக்கும்போது கீழ் நூல் உருண்டையாக சிக்கி துணி சுருங்குவது ஏன்? அதை எப்படி சரிசெய்வீர்கள்?",
                "hi": "सिलाई मशीन में नीचे का धागा गुच्छा बना रहा है और कपड़ा खिंच रहा है। आप टेंशन कैसे सेट करेंगे?",
            },
            "keywords": ["tension", "thread", "bobbin", "needle", "disc", "धागा", "टेंशन", "டென்ஷன்", "பாபின்"],
            "say": {
                "en": "Bottom thread bunching means top upper thread tension is too loose or needle threading missed the take-up lever. I will re-thread and tighten the upper tension disc.",
                "ta": "மேல் நூல் டென்ஷன் குறைவாக உள்ளது அல்லது டேக்-அப் லீவரில் நூல் சரியாக மாட்டவில்லை. மேல் டென்ஷன் டிஸ்க்கை சரிசெய்வேன்.",
                "hi": "नीचे धागा गुच्छा बनने का मतलब ऊपर की टेंशन डिस्क ढीली है या धागा टेक-अप लीवर से छूटा है। टेंशन टाइट करेंगे।",
            },
        },
        "say": {
            "en": "Bottom thread bunching means top upper thread tension is too loose or needle threading missed the take-up lever. I will re-thread and tighten the upper tension disc.",
            "ta": "மேல் நூல் டென்ஷன் குறைவாக உள்ளது அல்லது டேக்-அப் லீவரில் நூல் சரியாக மாட்டவில்லை. மேல் டென்ஷன் டிஸ்க்கை சரிசெய்வேன்.",
            "hi": "नीचे धागा गुच्छा बनने का मतलब ऊपर की टेंशन डिस्क ढीली है या धागा टेक-अप लीवर से छूटा है। टेंशन टाइट करेंगे।",
        },
    },
    "pottery": {
        "id": "pottery",
        "sector": "crafts",
        "name": "Pottery & Ceramics (Clay throwing, glazing, kiln operations)",
        "short": "Pottery & Ceramics",
        "menu": {"en": "Pottery & Ceramics", "ta": "மண்பாண்டம் & சுடுமண்", "hi": "मिट्टी के बर्तन व चीनी मिट्टी"},
        "sample_learner": "Meena K.",
        "sample_mentor": "Velu Udayar",
        "sample_hours": 28,
        "level": 3,
        "tags": ["Clay throwing", "Glazing", "Kiln firing"],
        "rubric": [
            ("Clay wedging and bubble removal", 92, None),
            ("Wheel centering and wall thickness consistency", 87, None),
            ("Rim trimming and base foot finishing", 84, None),
            ("Glaze coating thickness and uniformity", 86, None),
            ("Kiln stacking and temperature control", 76, "Allow slow cooling to prevent thermal shock cracks."),
        ],
        "viva": {
            "question": {
                "en": "After wheel throwing, your clay pot is cracking at the bottom base during drying before kiln firing. What caused this and how will you prevent it?",
                "ta": "சக்கரத்தில் செய்த மண்பாண்டம் உலரும்போது அடியில் வெடிப்பு ஏற்படுவது ஏன்? அதை எப்படி தடுப்பீர்கள்?",
                "hi": "चाक पर बना बर्तन सुखाते समय नीचे की पेंदी में दरार आ रही है। इसका क्या कारण है?",
            },
            "keywords": ["crack", "base", "drying", "thickness", "compress", "दरार", "पेंदी", "விரிசல்", "அடிபாகம்"],
            "say": {
                "en": "Base cracking happens when bottom clay is too thick compared to the walls, or water pooled in the center. I will compress the base firmly with a wooden rib and wire-trim evenly.",
                "ta": "அடிபாகத்தில் தண்ணீர் தங்கியதால் அல்லது சமமாக களிமண் அழுத்தப்படாததால் விரிசல் வருகிறது. அடிபாகத்தை மர பலகையால் அழுத்தி உலர வைப்பேன்.",
                "hi": "पेंदी की मिट्टी मोटी रह जाने या पानी जमा होने से दरार आती है। पेंदी को रिब से दबाकर बराबर मोटाई रखेंगे।",
            },
        },
        "say": {
            "en": "Base cracking happens when bottom clay is too thick compared to the walls, or water pooled in the center. I will compress the base firmly with a wooden rib and wire-trim evenly.",
            "ta": "அடிபாகத்தில் தண்ணீர் தங்கியதால் அல்லது சமமாக களிமண் அழுத்தப்படாததால் விரிசல் வருகிறது. அடிபாகத்தை மர பலகையால் அழுத்தி உலர வைப்பேன்.",
            "hi": "पेंदी की मिट्टी मोटी रह जाने या पानी जमा होने से दरार आती है। पेंदी को रिब से दबाकर बराबर मोटाई रखेंगे।",
        },
    },
    "weaving": {
        "id": "weaving",
        "sector": "crafts",
        "name": "Handloom & Weaving (Warping, loom setting, pattern execution)",
        "short": "Handloom & Weaving",
        "menu": {"en": "Handloom & Weaving", "ta": "கைத்தறி & நெசவு", "hi": "हथकरघा व बुनाई"},
        "sample_learner": "Subashree N.",
        "sample_mentor": "T. Padmanabhan",
        "sample_hours": 32,
        "level": 3,
        "tags": ["Warping", "Loom setting", "Pattern execution"],
        "rubric": [
            ("Warp tension balance across width", 91, None),
            ("Reed drafting and heddle threading accuracy", 89, None),
            ("Shuttle throw and selvedge edge straightness", 85, None),
            ("Beat-up regularity and pick count consistency", 88, None),
            ("Border pattern motif symmetry", 79, "Maintain consistent shuttle tension on border turns."),
        ],
        "viva": {
            "question": {
                "en": "On your handloom, the fabric selvedge edges are wavering inward in an hourglass shape instead of staying straight. What tension will you adjust?",
                "ta": "கைத்தறியில் துணியின் ஓரக்கரை நேராக இல்லாமல் உள்நோக்கி குறுகுவது ஏன்? எதை சீரமைப்பீர்கள்?",
                "hi": "हथकरघे पर कपड़े के किनारे अंदर की तरफ खिंच रहे हैं। आप इसे कैसे ठीक करेंगे?",
            },
            "keywords": ["selvedge", "weft", "shuttle", "tension", "warp", "किनारा", "ताना", "கரை", "ஊடை"],
            "say": {
                "en": "Inward selvedge draw-in happens when the weft shuttle yarn is thrown too tight. I will leave an angled arc in the weft pick before beating the reed and check temple stretchers.",
                "ta": "ஊடை நூல் அதிகமாக இழுக்கப்படுவதால் கரை உள்வாங்கும். ஊடை நூலை வளைவாக வைத்து தார்ப்பலகை கொண்டு சீராக தட்டுவேன்.",
                "hi": "बाने का धागा बहुत ज्यादा खिंचने से किनारा सिकुड़ता है। बाने को थोड़ा ढीला रखकर रीड से बराबर ठोकेंगे।",
            },
        },
        "say": {
            "en": "Inward selvedge draw-in happens when the weft shuttle yarn is thrown too tight. I will leave an angled arc in the weft pick before beating the reed and check temple stretchers.",
            "ta": "ஊடை நூல் அதிகமாக இழுக்கப்படுவதால் கரை உள்வாங்கும். ஊடை நூலை வளைவாக வைத்து தார்ப்பலகை கொண்டு சீராக தட்டுவேன்.",
            "hi": "बाने का धागा बहुत ज्यादा खिंचने से किनारा सिकुड़ता है। बाने को थोड़ा ढीला रखकर रीड से बराबर ठोकेंगे।",
        },
    },
    "carpentry": {
        "id": "carpentry",
        "sector": "crafts",
        "name": "Carpentry & Woodwork (Furniture joinery, sanding, polishing)",
        "short": "Carpentry & Woodwork",
        "menu": {"en": "Carpentry & Woodwork", "ta": "தச்சுவேலை & மரவேலை", "hi": "बढ़ईगीरी व काष्ठकला"},
        "sample_learner": "Aravind B.",
        "sample_mentor": "P. Arumugam Asari",
        "sample_hours": 26,
        "level": 3,
        "tags": ["Furniture joinery", "Chisel work", "Wood polishing"],
        "rubric": [
            ("Marking gauge and square precision", 93, None),
            ("Mortise and tenon joint fit tightness", 88, None),
            ("Hand plane surface flattening", 84, None),
            ("Progressive grit sanding smoothness", 86, None),
            ("French polish / sealant coats application", 77, "Apply thin sealer coats with adequate drying between coats."),
        ],
        "viva": {
            "question": {
                "en": "When cutting a mortise-and-tenon joint for a teak wood chair leg, the tenon is slightly loose and wobbles inside the mortise. What authentic shop fix will you apply?",
                "ta": "மர நாற்காலி கால் இணைப்பில் டெனன் தளர்வாக ஆடுகிறது. அதை இடைவெளியின்றி உறுதியாக எப்படி சரிசெய்வீர்கள்?",
                "hi": "कुर्सी के पाए का चूल (tenon) साल (mortise) में ढीला हो गया है। आप इसे कैसे मजबूत करेंगे?",
            },
            "keywords": ["wedge", "tenon", "glue", "mortise", "joint", "फन्नी", "चूल", "ஆப்பு", "டெனன்"],
            "say": {
                "en": "I will cut a fine kerf slot in the tenon end and drive a cross-grain hardwood wedge with carpenter glue for a permanent locked dovetail fit.",
                "ta": "டெனன் முனையில் சிறு பிளவு செய்து மர ஆப்பு மற்றும் பசையை வைத்து இறுக்கி ஆட்டமில்லாமல் செய்வேன்.",
                "hi": "चूल के सिरे पर चीरा लगाकर लकड़ी की फन्नी और फेविकोल ठोककर लॉक कर देंगे।",
            },
        },
        "say": {
            "en": "I will cut a fine kerf slot in the tenon end and drive a cross-grain hardwood wedge with carpenter glue for a permanent locked dovetail fit.",
            "ta": "டெனன் முனையில் சிறு பிளவு செய்து மர ஆப்பு மற்றும் பசையை வைத்து இறுக்கி ஆட்டமில்லாமல் செய்வேன்.",
            "hi": "चूल के सिरे पर चीरा लगाकर लकड़ी की फन्नी और फेविकोल ठोककर लॉक कर देंगे।",
        },
    },

    # 🏗️ Construction & Infrastructure
    "masonry": {
        "id": "masonry",
        "sector": "construction",
        "name": "Masonry & Bricklaying (Foundation work, plastering, tiling)",
        "short": "Masonry & Bricklaying",
        "menu": {"en": "Masonry & Bricklaying", "ta": "கொத்துவேலை & பூச்சு", "hi": "राजमिस्त्री व चिनाई"},
        "sample_learner": "Murugan C.",
        "sample_mentor": "K. Chinnasamy Mestri",
        "sample_hours": 36,
        "level": 3,
        "tags": ["Bricklaying", "Plastering", "Level & plumb"],
        "rubric": [
            ("Plumb line and spirit level verticality", 94, None),
            ("Mortar mix consistency and joint thickness", 87, None),
            ("Corner bond arrangement and alignment", 89, None),
            ("Wall surface plaster flatness and sponge finish", 82, None),
            ("Curing protocol and joint raking", 78, "Ensure proper water curing for 7 days minimum."),
        ],
        "viva": {
            "question": {
                "en": "While laying a 9-inch brick wall, your spirit level shows the wall leaning 5mm outward at the corner plumb line. How will you rectify this on the current course?",
                "ta": "9 இன்ச் செங்கல் சுவரில் மூலை மட்டம் 5 மி.மீ வெளிப்புறமாக சாய்கிறது. அதை அடுத்த வரிசையில் எப்படி நேராக்குவீர்கள்?",
                "hi": "9 इंच दीवार की चिनाई में कोना 5mm बाहर की तरफ झुक रहा है। आप इसे कैसे सीधा करेंगे?",
            },
            "keywords": ["plumb", "level", "trowel", "mortar", "tap", "साहुल", "करनी", "தூக்குநூல்", "மட்டம்"],
            "say": {
                "en": "I will tap the corner lead brick inward with the trowel butt, adjust the mortar bed thickness to 10mm, and re-drop the plumb bob from the reference bottom brick.",
                "ta": "கரண்டியின் பிடியால் செங்கலை உள்நோக்கி மெதுவாக தட்டி, கலவை கனத்தை சரிசெய்து தூக்குநூல் கொண்டு மீண்டும் சரிபார்ப்பேன்.",
                "hi": "करनी के दस्ते से ईंट को अंदर ठोकेंगे, मसाले की मोटाई 10mm सेट करके साहुल के धागे से मिलाएंगे।",
            },
        },
        "say": {
            "en": "I will tap the corner lead brick inward with the trowel butt, adjust the mortar bed thickness to 10mm, and re-drop the plumb bob from the reference bottom brick.",
            "ta": "கரண்டியின் பிடியால் செங்கலை உள்நோக்கி மெதுவாக தட்டி, கலவை கனத்தை சரிசெய்து தூக்குநூல் கொண்டு மீண்டும் சரிபார்ப்பேன்.",
            "hi": "करनी के दस्ते से ईंट को अंदर ठोकेंगे, मसाले की मोटाई 10mm सेट करके साहुल के धागे से मिलाएंगे।",
        },
    },
    "welding": {
        "id": "welding",
        "sector": "construction",
        "name": "Welding & Fabrication (Arc welding, structural alignment, gas cutting)",
        "short": "Welding & Fabrication",
        "menu": {"en": "Welding & Fabrication", "ta": "வெல்டிங் & ஃபேப்ரிகேஷன்", "hi": "वेल्डिंग व फैब्रिकेशन"},
        "sample_learner": "Ajith Kumar",
        "sample_mentor": "S. Anthony",
        "sample_hours": 30,
        "level": 3,
        "tags": ["Arc welding", "Joint fit-up", "Gas cutting"],
        "rubric": [
            ("Safety gear usage (welding helmet, leather apron)", 96, None),
            ("Bevel preparation and root gap setup", 88, None),
            ("Arc strike control and bead uniformity", 85, None),
            ("Slag removal and weld penetration check", 84, None),
            ("Distortion control and tack spacing", 75, "Use alternate side stitch welds to prevent plate distortion."),
        ],
        "viva": {
            "question": {
                "en": "In a horizontal fillet weld on 6mm MS plates, you observe undercut along the top toe of the bead. What arc length or travel speed caused this and how will you correct it?",
                "ta": "6 மி.மீ இரும்பு பிளேட் வெல்டிங்கில் மேல் விளிம்பில் பள்ளம் (undercut) விழுகிறது. இதை எப்படி தடுப்பீர்கள்?",
                "hi": "6mm प्लेट की वेल्डिंग में ऊपर की तरफ गड्ढा (undercut) बन रहा है। करंट और एंगल कैसे ठीक करेंगे?",
            },
            "keywords": ["undercut", "arc", "current", "amp", "electrode", "गड्ढा", "करंट", "ஆம்பியர்", "ஆர்க்"],
            "say": {
                "en": "Undercut is caused by too long an arc length or excessive welding current. I will lower the amperage by 10 amps, hold a shorter 2mm arc, and pause at the top toe.",
                "ta": "அதிக ஆம்பியர் அல்லது நீளமான ஆர்க் காரணமாக அண்டர்கட் வருகிறது. ஆம்பியரை 10 குறைத்து, எலக்ட்ரோடை குறுகிய இடைவெளியில் சீராக நகர்த்துவேன்.",
                "hi": "आर्क लंबा होने या ज्यादा करंट से गड्ढा बनता है। करंट 10 एम्पीयर कम करेंगे और इलेक्ट्रोड को पास रखकर चलेंगे।",
            },
        },
        "say": {
            "en": "Undercut is caused by too long an arc length or excessive welding current. I will lower the amperage by 10 amps, hold a shorter 2mm arc, and pause at the top toe.",
            "ta": "அதிக ஆம்பியர் அல்லது நீளமான ஆர்க் காரணமாக அண்டர்கட் வருகிறது. ஆம்பியரை 10 குறைத்து, எலக்ட்ரோடை குறுகிய இடைவெளியில் சீராக நகர்த்துவேன்.",
            "hi": "आर्क लंबा होने या ज्यादा करंट से गड्ढा बनता है। करंट 10 एम्पीयर कम करेंगे और इलेक्ट्रोड को पास रखकर चलेंगे।",
        },
    },
    "painting": {
        "id": "painting",
        "sector": "construction",
        "name": "House Painting & Polishing (Wall preparation, texture painting, putty work)",
        "short": "House Painting & Polishing",
        "menu": {"en": "House Painting & Polishing", "ta": "வர்ணம் பூசுதல் & புட்டி", "hi": "पेंटिंग व पुट्टी कार्य"},
        "sample_learner": "Deepak Sharma",
        "sample_mentor": "B. Ramanathan",
        "sample_hours": 22,
        "level": 3,
        "tags": ["Wall putty", "Surface prep", "Roller & spray finish"],
        "rubric": [
            ("Surface scraping and primer application", 91, None),
            ("Two-coat putty application and sanding smoothness", 89, None),
            ("Masking tape boundary sharpness on edges", 86, None),
            ("Roller stroke consistency without overlap lap marks", 84, None),
            ("Coat thickness uniformity and drying intervals", 78, "Maintain 4-hour drying interval between top coats."),
        ],
        "viva": {
            "question": {
                "en": "After applying primer and two coats of wall putty on interior plaster, you notice fine blistering bubbles appearing on the wall surface. What is the cause and remedy?",
                "ta": "சுவரில் புட்டி பூசிய பிறகு சிறு சிறு குமிழ்கள் (bubbles) தோன்றுகிறது. இதற்கு என்ன காரணம் மற்றும் தீர்வு?",
                "hi": "दीवार पर प्राइमर और पुट्टी लगाने के बाद छोटे-छोटे फफोले (bubbles) दिख रहे हैं। इसका क्या कारण और समाधान है?",
            },
            "keywords": ["bubble", "blister", "moisture", "dry", "scrape", "फफोले", "नमी", "ஈரப்பதம்", "குமிழ்கள்"],
            "say": {
                "en": "Bubbling happens due to trapped moisture in fresh plaster or applying the second putty coat before the first dried. I will scrape the blisters, let the plaster cure dry, spot-prime, and re-skim.",
                "ta": "சுவரில் உள்ள ஈரப்பதம் அல்லது முதல் கோட் காயும் முன் அடுத்த கோட் பூசியதால் குமிழ்கள் வருகின்றன. அதை சுரண்டி உலர்த்தி மீண்டும் புட்டி போடுவேன்.",
                "hi": "प्लास्टर में नमी रहने या पहली कोट सूखे बिना दूसरी कोट लगाने से फफोले आते हैं। खुरचकर सूखने देंगे और दोबारा पुट्टी लगाएंगे।",
            },
        },
        "say": {
            "en": "Bubbling happens due to trapped moisture in fresh plaster or applying the second putty coat before the first dried. I will scrape the blisters, let the plaster cure dry, spot-prime, and re-skim.",
            "ta": "சுவரில் உள்ள ஈரப்பதம் அல்லது முதல் கோட் காயும் முன் அடுத்த கோட் பூசியதால் குமிழ்கள் வருகின்றன. அதை சுரண்டி உலர்த்தி மீண்டும் புட்டி போடுவேன்.",
            "hi": "प्लास्टर में नमी रहने या पहली कोट सूखे बिना दूसरी कोट लगाने से फफोले आते हैं। खुरचकर सूखने देंगे और दोबारा पुट्टी लगाएंगे।",
        },
    },
}

# (title, place, skill tag). SAMPLE listings; production reads SIDH / ONEST.
LISTINGS: dict[str, list[tuple[str, str, str]]] = {
    # Technical
    "electrical": [
        ("Apprentice wireman, domestic", "Chengalpattu district", "Domestic wiring"),
        ("Solar rooftop helper", "Kanchipuram district", "Safe isolation"),
        ("Maintenance electrician trainee", "Chennai suburbs", "Relay control"),
    ],
    "plumbing": [
        ("Plumbing apprentice (residential)", "Coimbatore district", "Pipe threading"),
        ("Sanitary fittings installer trainee", "Chennai metro", "Fixture installation"),
        ("Pipeline maintenance assistant", "Tiruchirappalli district", "Leak diagnostics"),
    ],
    "hvac": [
        ("AC service technician trainee", "Chennai suburbs", "Gas charging"),
        ("Commercial chiller apprentice", "Sriperumbudur industrial belt", "Compressor servicing"),
        ("HVAC duct installer assistant", "Madurai district", "Flaring and brazing"),
    ],
    "automobile": [
        ("Two-wheeler service assistant", "Salem district", "Two-wheeler service"),
        ("Auto electrical apprentice", "Hosur automotive cluster", "Harness wiring"),
        ("Garage technician helper", "Vellore district", "Engine tuning"),
    ],
    "solar": [
        ("Solar installer trainee", "Chengalpattu district", "Solar PV basics"),
        ("Street-light maintenance apprentice", "Kanchipuram district", "DC wiring safety"),
        ("Electrician helper", "Chennai suburbs", "Panel mounting"),
    ],

    # Crafts
    "tailoring": [
        ("Sewing operator trainee", "Chennai suburbs", "Garment stitching"),
        ("Tailoring apprentice", "Chengalpattu district", "Seam finishing"),
        ("Uniform stitching unit, women-led", "Kanchipuram district", "Measurement"),
    ],
    "pottery": [
        ("Artisan pottery apprentice", "Vilachery, Madurai", "Clay throwing"),
        ("Ceramic studio helper", "Auroville craft cluster", "Glazing"),
        ("Terracotta craft unit trainee", "Manamadurai cluster", "Kiln firing"),
    ],
    "weaving": [
        ("Handloom weaver apprentice", "Kanchipuram silk cluster", "Warping"),
        ("Loom setting assistant", "Salem textile park", "Loom setting"),
        ("Traditional weaving artisan unit", "Arani cluster", "Pattern execution"),
    ],
    "carpentry": [
        ("Furniture joinery trainee", "Chennai suburbs", "Furniture joinery"),
        ("Interior woodwork apprentice", "Coimbatore furniture cluster", "Wood polishing"),
        ("Modular kitchen installer helper", "Kanchipuram district", "Chisel work"),
    ],

    # Construction
    "masonry": [
        ("Masonry & tile laying apprentice", "Chennai construction cluster", "Level & plumb"),
        ("Brickwork assistant", "Chengalpattu infrastructure project", "Bricklaying"),
        ("Plastering technician trainee", "Tiruvallur district", "Plastering"),
    ],
    "welding": [
        ("Structural welder apprentice", "Ennore industrial estate", "Arc welding"),
        ("Metal fabrication helper", "Ambattur industrial estate", "Joint fit-up"),
        ("Gas cutting & fitting trainee", "Ranipet SIPCOT", "Gas cutting"),
    ],
    "painting": [
        ("Interior wall finisher apprentice", "Chennai metro", "Wall putty"),
        ("Commercial painting helper", "Coimbatore suburbs", "Roller & spray finish"),
        ("Wood & metal polisher assistant", "Kanchipuram district", "Surface prep"),
    ],
}

