from datetime import date

def get_default_levels():
    today = str(date.today()) 

    return {
    "Mathematics": {
        "Number System": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
        "Algebra": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
        "Coordinate Geometry": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
        "Geometry": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
        "Trigonometry": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
        "Mensuration": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
        "Statistics and Probability": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
    },
    "Physics": {
        "Light – Reflection and Refraction": {
            "level": "Beginner",
            "lastUpdated": today,
            "subtopics": {
                "Reflection of Light": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Laws of Reflection": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Image formation by plane mirror": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Spherical mirrors: concave and convex": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Image formation by spherical mirrors": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Mirror formula and magnification": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Refraction of Light": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Laws of Refraction": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Refraction through a glass slab": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Refraction by spherical lenses": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Image formation by lenses": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Lens formula and magnification": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Power of a lens": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
            },
        },
        "The Human Eye and the Colourful World": {
            "level": "Beginner",
            "lastUpdated": today,
            "subtopics": {
                "Structure and working of the human eye": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Defects of vision and their correction": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Myopia (short-sightedness)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Hypermetropia (long-sightedness)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Presbyopia": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Refraction of light through a prism": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Dispersion of white light by a prism": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Atmospheric refraction": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Scattering of light": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Tyndall effect": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Why the sky is blue": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Why the sun appears reddish at sunrise and sunset": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
        }},
        "Electricity": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
                "Electric current and circuit": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Electric potential and potential difference": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Ohm’s law": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Resistance": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Factors affecting resistance": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Resistivity":{"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Resistance in series and parallel": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Heating effect of electric current": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Power and energy": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
            }},
        "Magnetic Effects of Electric Current": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
                "Magnetic field and field lines": {"level": "Beginner", "lastUpdated": today,"subtopics": None },
                "Magnetic field due to a current-carrying conductor": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Straight conductor": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Circular loop": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Solenoid": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Force on a current-carrying conductor in a magnetic field": {"level": "Beginner", "lastUpdated": today,"subtopics": None },
                "Fleming’s Left-Hand Rule": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Electric motor (principle and working)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Electromagnetic induction": {"level": "Beginner", "lastUpdated": today,"subtopics": None },
                "Fleming’s Right-Hand Rule": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Electric generator (principle and working)": {"level": "Beginner", "lastUpdated": today,"subtopics": None     },
                "Domestic electric circuits": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
            }},
        "Sources of Energy": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
                "Different sources of energy": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Conventional sources: fossil fuels, thermal power, hydroelectric power": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Non-conventional sources: solar energy, wind energy, tidal energy, etc.": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Renewable and non-renewable energy sources": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Environmental consequences": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
            }},
    },
    "Chemistry": {
        "Chemical Reactions and Equations": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
                "Chemical Equations": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Types of Chemical Reactions:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Combination reaction": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Decomposition reaction": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Displacement reaction": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Double displacement reaction": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Effects of Oxidation in Everyday Life (corrosion, rancidity)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Balancing chemical equations": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
        }},
        "Acids, Bases and Salts": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
                "Properties of acids and bases": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Reactions of acids and bases with:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Metals": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Metal carbonates and metal hydrogen carbonates": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Metal oxides and non-metal oxides": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Neutralization reactions": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "pH scale and importance of pH in daily life": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Salts: preparation, properties, uses of important salts:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Sodium chloride (common salt)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Baking soda": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Washing soda": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Plaster of Paris": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
            }},
        "Metals and Non-metals": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
                "Physical and chemical properties of metals and non-metals": {"level": "Beginner", "lastUpdated": today,"subtopics": None   },
        "Reactions of metals with:": {"level": "Beginner", "lastUpdated": today,"subtopics": None  },
        "Air": { "level": "Beginner", "lastUpdated": today,"subtopics": None     },
        "Water": {"level": "Beginner", "lastUpdated": today,"subtopics": None },
        "Acids": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
        "Reactivity series": {"level": "Beginner", "lastUpdated": today,"subtopics": None },
        "Ionic bonding": {"level": "Beginner", "lastUpdated": today,"subtopics": None  },
        "Extraction of metals:": {"level": "Beginner", "lastUpdated": today,"subtopics": None  },
        "Ores and minerals": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
        "Metallurgy (concentration, roasting, reduction)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
        "Corrosion and prevention": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
            }},
        "Carbon and Its Compounds": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
                "Covalent bonding in carbon compounds": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Allotropes of carbon": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Hydrocarbons: saturated and unsaturated": {  "level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Homologous series": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Nomenclature of carbon compounds": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Chemical properties of carbon compounds:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Combustion": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Oxidation": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Addition and substitution reactions": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Important carbon compounds:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Ethanol (properties and reactions)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Ethanoic acid (properties and reactions)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Soaps and detergents": {  "level": "Beginner", "lastUpdated": today,"subtopics": None}
            }},
        "Periodic Classification of Elements": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
                "Early attempts at classification (Dobereiner’s Triads, Newlands’ Octaves)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Mendeleev’s Periodic Table": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Modern Periodic Table": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Trends in the Modern Periodic Table:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Atomic size": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Valency": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Metallic and non-metallic properties": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
            }},
    },
    "Biology": {
        "Life Processes": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
                "What are life processes?": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Nutrition:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Autotrophic (photosynthesis in plants)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Heterotrophic (holozoic in humans)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Respiration:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Aerobic and anaerobic": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Human respiratory system": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Transportation:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Transport in plants (xylem and phloem)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Circulatory system in humans (heart, blood, blood vessels)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Excretion:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Excretory system in humans": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Excretion in plants": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
            }},
        "Control and Coordination": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
                "Coordination in animals:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Nervous system in humans (structure and function of neuron, reflex action, brain)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Endocrine system (hormones in animals)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Coordination in plants:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Growth and movement (tropism)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Plant hormones": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
            }},
        "How do Organisms Reproduce?": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
                "Reproduction: why do organisms reproduce?": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Asexual reproduction:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Fission, fragmentation, regeneration": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Budding, spore formation, vegetative propagation": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Sexual reproduction:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "In flowering plants": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "In humans (male and female reproductive systems, menstrual cycle, fertilization)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Reproductive health:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Birth control methods": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "STDs": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
            }},
        "Heredity and Evolution": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
                "Heredity:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Mendel’s experiments": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Laws of inheritance": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Sex determination": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Evolution:": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Evolution and classification": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Tracing evolutionary relationships (fossils, homologous/analogous organs)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Speciation": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Evolution vs. progress": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
            }},
        "Our Environment": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
              "Ecosystem (components, food chains/webs, energy flow)": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
               "Ozone layer and its depletion": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
               "Waste management (biodegradable and non-biodegradable)": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
            }},
        "Sustainable Management of Natural Resources": {
            "level": "Beginner", 
            "lastUpdated": today,
            "subtopics": {
               "Why do we need to manage resources?": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
               "Forest and wildlife conservation": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
               "Water management": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
               "Coal and petroleum": {"level": "Beginner", "lastUpdated": today,"subtopics": None},
                "Reduce, reuse, recycle (3Rs)": {"level": "Beginner", "lastUpdated": today,"subtopics": None}
            }},
    },
}

