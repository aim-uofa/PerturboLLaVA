import argparse
import requests
import json
import time
import random
import hmac
import hashlib
import re
from tqdm import tqdm
import multiprocessing
from multiprocessing import Lock

ENTITY_RELATIONSHIPS_GENERATION_PROMPT = """
    -Goal-
    Given a text that is potentially relevant to this activity and a list of entity types, identify all objects, their attributes, and relationships among the identified objects.

    -Steps-
    1. Identify all objects. For each identified object, extract the following information:
    - object_name: Name of the object, capitalized.
    - object_attribute: An attribute of the object (e.g., color, size, position).
    Format each object as ("object"{{tuple_delimiter}}<object_name>{{tuple_delimiter}}<object_attribute>)

    2. From the objects identified in step 1, identify all pairs of (source_object, target_object) that are *clearly related* to each other.
    For each pair of related objects, extract the following information:
    - source_object: name of the source object, as identified in step 1
    - target_object: name of the target object, as identified in step 1
    - relationship_description: explanation as to why you think the source object and the target object are related to each other
    - relationship_strength: an integer score between 1 to 10, indicating strength of the relationship between the source object and target object
    Format each relationship as ("relationship"{{tuple_delimiter}}<source_object>{{tuple_delimiter}}<target_object>{{tuple_delimiter}}<relationship_description>{{tuple_delimiter}}<relationship_strength>)

    3. Return output in English as a numbered list of all the objects and relationships identified in steps 1 and 2. Use {{record_delimiter}} as the list delimiter.


    4. Only translate descriptions if necessary.

    5. When finished, output {{completion_delimiter}}.

    ######################
    -Examples-
    ######################
    Example 1:
    Text:
    There is a big water area with blue water. Most of it is relatively calm with small waves and streams, however the section on the left has a lot of waves in the wake of a boat. They curve up, and there is white to indicate where the water is splashing. There is a boat that is mostly red and black with white on the front. The bottom is red and then it is black above that. There are black tires that go in a row all along the side of the boat except for the back. The right half of the boat is taller. It has a white structure that comes up. There is a rail that goes along it. There are ladders that lead up to the higher platforms. There are windows on the structure. There is a lot of equipment all over the top of the boat, including a yellow rounded part. Behind it, there is a big white boat. The left 2/3 is much higher and taller and the right third is very low and has a platform. There is writing on the side that is red for one word and then blue for two words. There are rectangular windows going against the side that go in even rows and are evenly spaced and shaped. There are more windows by the front. There are rails along it. The boat goes up and is tallest in the middle. There are three long equal orange lifeboats hanging in the middle. There are more windows that go along as the building goes up. In the very middle there is a wall where it slants up and is thinner on the top. Behind that, there is a pointed white tower coming up. The bottom has straight sides that slant in. There is then a rounded platform that has a white rail curving around it. There are white beams that slant up from there to meet together. It is rounded at the very top. There are many poles and beams coming from it. Behind it on the right, there is a crane coming up. It has slanted orange poles and then smaller slanted lines going between it. It comes up to a rounded part at the top. To the far right, there is a white boat. The very bottom has a red strip. There is a horizontal blue line about 1/3 from the bottom in the middle. There is a smaller blue strip by the back. The left side of the boat is curved in the front. There is a lot of equipment in it. The middle portion of the boat comes up higher. It has a structure at the front that has a lot of rectangular windows that are going across it in a row. There is a lot of equipment all along the boat. It is a little shorter on the back. The side is very weathered and discolored with a part that is black near the front in the middle. It has orange around it. There are some big rounded orange pieces of equipment coming up from the back. They have black parts on top. There is more orange equipment on the left as well as white poles coming up from the lower section in the middle and also from the top left. On the left back, there is a wall. It is very weathered and gray. The top half is a lighter gray and the bottom is mostly black. There are black streaks coming up from the bottom section. It has a mostly straight top and sides. It goes into the water. The wall continues to the right. It is very weathered and gray. The top half is lighter and the bottom is darker. There are a lot of places where it is discolored. There are brown and orange streaks coming down on the top ¼. There is a black protrusion that curves out on the top left of the wall. The right 2/3 looks darker because it is in the shadows. It has a mostly straight top and sides. It goes into the water. There are many buildings on the shore. There is a building on the far back left. It is tan colored. It is lower on the front with two blue lines going up on the left. There are two horizontal thin strips on the right of that section. Above that on the right there is a section that juts out. To the left of that there are three sections coming up that have rows of evenly spaced and shaped windows. There are rectangular white signs with images on those sections. The building is tallest on the back right, where it has a brown sloping roof. To the left there are green metal poles that go across and have slanting lines under there. There is another narrow part that comes up in the middle. There are also slanting brown roofs on the section in the middle. On the left there is an orange square at the top of the wall. The building extends out to the right. There is also a building about 40% from the right. It is a curved building with evenly spaced and shaped rows of gray blocks that slant up. There are three narrow walls that extend and curve out to the left. There are two rows of three rectangular windows that appear dark behind them on the right side. The top windows are a little smaller. There are white swirling walls that go around the top and are highest on the left about one third from the end of the building. On the left side, there is a gray tower going up. It is rectangular shaped with 4 gray poles. There are slanting and horizontal poles along it. It has even identical sections as it goes up. It is a little wider on the top. The sky is mostly blue and clear and is a little lighter as it goes down. There are a few wispy clouds in the top left and bottom right.

    Output:
    1. ("object"{{tuple_delimiter}}WATER AREA{{tuple_delimiter}}big)
    {{record_delimiter}}
    2. ("object"{{tuple_delimiter}}WATER{{tuple_delimiter}}blue)
    {{record_delimiter}}
    3. ("object"{{tuple_delimiter}}WATER{{tuple_delimiter}}relatively calm)
    {{record_delimiter}}
    4. ("object"{{tuple_delimiter}}WAVES{{tuple_delimiter}}small)
    {{record_delimiter}}
    5. ("object"{{tuple_delimiter}}STREAMS{{tuple_delimiter}}small)
    {{record_delimiter}}
    6. ("object"{{tuple_delimiter}}SECTION ON THE LEFT{{tuple_delimiter}}has a lot of waves)
    {{record_delimiter}}
    7. ("object"{{tuple_delimiter}}BOAT{{tuple_delimiter}}creating wake)
    {{record_delimiter}}
    8. ("object"{{tuple_delimiter}}WAVES{{tuple_delimiter}}curve up)
    {{record_delimiter}}
    9. ("object"{{tuple_delimiter}}WHITE SPLASHES{{tuple_delimiter}}indicate water splashing)
    {{record_delimiter}}
    10. ("object"{{tuple_delimiter}}BOAT{{tuple_delimiter}}mostly red and black)
    {{record_delimiter}}
    11. ("object"{{tuple_delimiter}}FRONT OF BOAT{{tuple_delimiter}}white)
    {{record_delimiter}}
    12. ("object"{{tuple_delimiter}}BOTTOM OF BOAT{{tuple_delimiter}}red)
    {{record_delimiter}}
    13. ("object"{{tuple_delimiter}}AREA ABOVE BOTTOM{{tuple_delimiter}}black)
    {{record_delimiter}}
    14. ("object"{{tuple_delimiter}}BLACK TIRES{{tuple_delimiter}}in a row along the side of the boat)
    {{record_delimiter}}
    15. ("object"{{tuple_delimiter}}BACK OF BOAT{{tuple_delimiter}}no black tires)
    {{record_delimiter}}
    16. ("object"{{tuple_delimiter}}RIGHT HALF OF BOAT{{tuple_delimiter}}taller)
    {{record_delimiter}}
    17. ("object"{{tuple_delimiter}}WHITE STRUCTURE{{tuple_delimiter}}rises from boat)
    {{record_delimiter}}
    18. ("object"{{tuple_delimiter}}RAIL{{tuple_delimiter}}goes along structure)
    {{record_delimiter}}
    19. ("object"{{tuple_delimiter}}LADDERS{{tuple_delimiter}}lead up to higher platforms)
    {{record_delimiter}}
    20. ("object"{{tuple_delimiter}}PLATFORMS{{tuple_delimiter}}higher)
    {{record_delimiter}}
    21. ("object"{{tuple_delimiter}}WINDOWS{{tuple_delimiter}}on the structure)
    {{record_delimiter}}
    22. ("object"{{tuple_delimiter}}EQUIPMENT{{tuple_delimiter}}all over the top of the boat)
    {{record_delimiter}}
    23. ("object"{{tuple_delimiter}}YELLOW ROUNDED PART{{tuple_delimiter}}included in equipment)
    {{record_delimiter}}
    24. ("object"{{tuple_delimiter}}BIG WHITE BOAT{{tuple_delimiter}}behind the first boat)
    {{record_delimiter}}
    25. ("object"{{tuple_delimiter}}LEFT TWO-THIRDS OF BIG WHITE BOAT{{tuple_delimiter}}much higher and taller)
    {{record_delimiter}}
    26. ("object"{{tuple_delimiter}}RIGHT THIRD OF BIG WHITE BOAT{{tuple_delimiter}}very low)
    {{record_delimiter}}
    27. ("object"{{tuple_delimiter}}PLATFORM{{tuple_delimiter}}on right third of big white boat)
    {{record_delimiter}}
    28. ("object"{{tuple_delimiter}}WRITING ON SIDE{{tuple_delimiter}}one word red, two words blue)
    {{record_delimiter}}
    29. ("object"{{tuple_delimiter}}RECTANGULAR WINDOWS{{tuple_delimiter}}evenly spaced and shaped)
    {{record_delimiter}}
    30. ("object"{{tuple_delimiter}}MORE WINDOWS{{tuple_delimiter}}by the front)
    {{record_delimiter}}
    31. ("object"{{tuple_delimiter}}RAILS{{tuple_delimiter}}along the big white boat)
    {{record_delimiter}}
    32. ("object"{{tuple_delimiter}}BOAT{{tuple_delimiter}}tallest in the middle)
    {{record_delimiter}}
    33. ("object"{{tuple_delimiter}}THREE LONG EQUAL ORANGE LIFEBOATS{{tuple_delimiter}}hanging in the middle)
    {{record_delimiter}}
    34. ("object"{{tuple_delimiter}}ADDITIONAL WINDOWS{{tuple_delimiter}}as building goes up)
    {{record_delimiter}}
    35. ("object"{{tuple_delimiter}}WALL{{tuple_delimiter}}in very middle, slants up, thinner on top)
    {{record_delimiter}}
    36. ("object"{{tuple_delimiter}}POINTED WHITE TOWER{{tuple_delimiter}}coming up behind the wall)
    {{record_delimiter}}
    37. ("object"{{tuple_delimiter}}BOTTOM OF TOWER{{tuple_delimiter}}straight sides that slant in)
    {{record_delimiter}}
    38. ("object"{{tuple_delimiter}}ROUNDED PLATFORM{{tuple_delimiter}}has a white rail curving around)
    {{record_delimiter}}
    39. ("object"{{tuple_delimiter}}WHITE BEAMS{{tuple_delimiter}}slant up to meet together)
    {{record_delimiter}}
    40. ("object"{{tuple_delimiter}}VERY TOP OF TOWER{{tuple_delimiter}}rounded)
    {{record_delimiter}}
    41. ("object"{{tuple_delimiter}}POLES AND BEAMS{{tuple_delimiter}}coming from the tower)
    {{record_delimiter}}
    42. ("object"{{tuple_delimiter}}CRANE{{tuple_delimiter}}behind tower on the right)
    {{record_delimiter}}
    43. ("object"{{tuple_delimiter}}SLANTED ORANGE POLES{{tuple_delimiter}}part of crane)
    {{record_delimiter}}
    44. ("object"{{tuple_delimiter}}SMALLER SLANTED LINES{{tuple_delimiter}}between orange poles)
    {{record_delimiter}}
    45. ("object"{{tuple_delimiter}}ROUNDED PART AT TOP OF CRANE{{tuple_delimiter}}where crane ends)
    {{record_delimiter}}
    46. ("relationship"{{tuple_delimiter}}WAVES{{tuple_delimiter}}WATER{{tuple_delimiter}}The waves are part of the water area{{tuple_delimiter}}9)
    {{record_delimiter}}
    47. ("relationship"{{tuple_delimiter}}STREAMS{{tuple_delimiter}}WATER{{tuple_delimiter}}The streams are within the water area{{tuple_delimiter}}9)
    {{record_delimiter}}
    48. ("relationship"{{tuple_delimiter}}SECTION ON THE LEFT{{tuple_delimiter}}WATER AREA{{tuple_delimiter}}The section on the left is part of the water area{{tuple_delimiter}}8)
    {{record_delimiter}}
    49. ("relationship"{{tuple_delimiter}}WAVES{{tuple_delimiter}}BOAT{{tuple_delimiter}}The waves are in the wake of the boat{{tuple_delimiter}}9)
    {{record_delimiter}}
    50. ("relationship"{{tuple_delimiter}}WHITE SPLASHES{{tuple_delimiter}}WATER{{tuple_delimiter}}The white indicates water splashing{{tuple_delimiter}}7)
    {{record_delimiter}}
    51. ("relationship"{{tuple_delimiter}}WHITE STRUCTURE{{tuple_delimiter}}BOAT{{tuple_delimiter}}The white structure is part of the boat{{tuple_delimiter}}9)
    {{record_delimiter}}
    52. ("relationship"{{tuple_delimiter}}BLACK TIRES{{tuple_delimiter}}BOAT{{tuple_delimiter}}The black tires are along the side of the boat{{tuple_delimiter}}8)
    {{record_delimiter}}
    53. ("relationship"{{tuple_delimiter}}LADDERS{{tuple_delimiter}}PLATFORMS{{tuple_delimiter}}The ladders lead up to the higher platforms{{tuple_delimiter}}8)
    {{record_delimiter}}
    54. ("relationship"{{tuple_delimiter}}WINDOWS{{tuple_delimiter}}STRUCTURE{{tuple_delimiter}}The windows are on the structure{{tuple_delimiter}}8)
    {{record_delimiter}}
    55. ("relationship"{{tuple_delimiter}}EQUIPMENT{{tuple_delimiter}}BOAT{{tuple_delimiter}}The equipment is all over the top of the boat{{tuple_delimiter}}9)
    {{record_delimiter}}
    56. ("relationship"{{tuple_delimiter}}YELLOW ROUNDED PART{{tuple_delimiter}}EQUIPMENT{{tuple_delimiter}}The yellow rounded part is included in the equipment{{tuple_delimiter}}8)
    {{record_delimiter}}
    57. ("relationship"{{tuple_delimiter}}BIG WHITE BOAT{{tuple_delimiter}}FIRST BOAT{{tuple_delimiter}}The big white boat is behind the first boat{{tuple_delimiter}}7)
    {{record_delimiter}}
    58. ("relationship"{{tuple_delimiter}}RECTANGULAR WINDOWS{{tuple_delimiter}}BIG WHITE BOAT{{tuple_delimiter}}The windows are on the side of the big white boat{{tuple_delimiter}}8)
    {{record_delimiter}}
    59. ("relationship"{{tuple_delimiter}}ORANGE LIFEBOATS{{tuple_delimiter}}BIG WHITE BOAT{{tuple_delimiter}}The lifeboats are hanging in the middle of the big white boat{{tuple_delimiter}}8)
    {{record_delimiter}}
    60. ("relationship"{{tuple_delimiter}}ADDITIONAL WINDOWS{{tuple_delimiter}}BUILDING{{tuple_delimiter}}More windows as the building goes up{{tuple_delimiter}}7)
    {{record_delimiter}}
    61. ("relationship"{{tuple_delimiter}}POINTED WHITE TOWER{{tuple_delimiter}}WALL{{tuple_delimiter}}The tower is coming up behind the wall{{tuple_delimiter}}7)
    {{record_delimiter}}
    62. ("relationship"{{tuple_delimiter}}CRANE{{tuple_delimiter}}TOWER{{tuple_delimiter}}The crane is behind the tower on the right{{tuple_delimiter}}6)
    {{record_delimiter}}
    63. ("relationship"{{tuple_delimiter}}SLANTED ORANGE POLES{{tuple_delimiter}}CRANE{{tuple_delimiter}}The slanted orange poles are part of the crane{{tuple_delimiter}}9)
    {{record_delimiter}}
    64. ("relationship"{{tuple_delimiter}}SMALLER SLANTED LINES{{tuple_delimiter}}CRANE{{tuple_delimiter}}The smaller slanted lines are between the orange poles on the crane{{tuple_delimiter}}8)
    {{record_delimiter}}
    65. ("relationship"{{tuple_delimiter}}ROUNDED PLATFORM{{tuple_delimiter}}TOWER{{tuple_delimiter}}The rounded platform is part of the tower{{tuple_delimiter}}8)
    {{record_delimiter}}
    66. ("relationship"{{tuple_delimiter}}WHITE BEAMS{{tuple_delimiter}}TOWER{{tuple_delimiter}}The white beams slant up from the platform to meet together on the tower{{tuple_delimiter}}9)
    {{completion_delimiter}}

    ######################
    -Real Data-
    ######################
    entity_types: OBJECT, ATTRIBUTE
    text: {input_text}
    ######################
    output:
    """

HALL_PROMPT = """

-Goal-

Given two lists of objects, attributes, and relationships extracted from a ground truth (GT) caption and a Vision-Language Model (VLM) caption—both numbered—compare the VLM list to the GT list to identify any incorrect objects, attributes, or relationships in the VLM caption. An incorrect object, attribute, or relationship (hallucination) is one that does not correspond to any in the GT list. Importantly, use your language understanding to assess whether objects, attributes, and relationships convey the same meaning, even if expressed differently.

Instructions

Input Data:

You will be provided with two numbered lists:

GT List: The ground truth caption's list of objects, attributes, and relationships.
VLM List: The VLM caption's list of objects, attributes, and relationships.
Comparison Process:

Step 1: For each entry in the VLM list, determine if it exists in the GT list.

For Objects:
If an object in the VLM list matches an object in the GT list (considering synonyms and similar expressions), proceed to compare its attributes and relationships.
If an object in the VLM list does not exist in the GT list, classify it as an incorrect object (hallucination).
Important: If an incorrect object appears multiple times in the VLM list (with different attributes or relationships), it counts as one hallucination.
For Attributes:
An attribute in the VLM list matches the GT list if there is an object with the same name (or similar) and the attribute conveys the same meaning as an attribute of that object in the GT list, even if the wording is different.
If an object exists in both lists but has attributes in the VLM list that are not present in the GT list, classify each incorrect attribute as a hallucination.
For Relationships:
A relationship in the VLM list matches the GT list if there is a relationship with the same source object and target object, and the relationship description conveys the same meaning as a relationship in the GT list, even if the wording is different.
If a relationship in the VLM list involves an incorrect object (one not present in the GT list), it is considered part of the hallucination for that object and does not count separately.
If a relationship involves correct objects but introduces a new or significantly different relationship not present in the GT list, classify it as an incorrect relationship (hallucination).
Step 2: Compile the list of hallucinations.

Objects:
List each incorrect object (counts as one hallucination per object, regardless of how many times it appears).
Attributes:
List each incorrect attribute separately (each counts as a separate hallucination).
Relationships:
List each incorrect relationship separately (each counts as a separate hallucination), unless it involves an incorrect object already counted.
Output Instructions:

Analysis:
Provide a brief analysis explaining which entries are incorrect and why, following the format:

**Analysis:**

- **Entry [Serial Number] in VLM List:** [Entry Details]
  - [Explanation of why it's incorrect]
Incorrect Serial Numbers:
Collect all the serial numbers from the VLM list that correspond to incorrect objects (one per incorrect object), incorrect attributes, and incorrect relationships (excluding those involving already counted incorrect objects).
Present them in a single list, in numerical order, separated by commas.
Example: Incorrect Serial Numbers: 3, 6, 9
Do not include any additional explanations or text in the output.
Notes:

Semantic Matching:
Use your language understanding to determine whether objects, attributes, or relationships in the VLM list and GT list convey the same meaning.
Minor variations in wording or phrasing that convey the same meaning should be considered a match.
Only consider an object, attribute, or relationship incorrect if it introduces new information not present in the GT list or if the meaning significantly differs.
Case Sensitivity:
Object names and attributes are case-insensitive for matching purposes.
Ignore Serial Numbers in GT List:
Use the serial numbers only from the VLM list when reporting incorrect entries.
Example:

GT List:

("object"{{tuple_delimiter}}INDOOR MALL{{tuple_delimiter}}has three illuminated escalators)
("object"{{tuple_delimiter}}ESCALATORS{{tuple_delimiter}}illuminated)
("object"{{tuple_delimiter}}MALL{{tuple_delimiter}}various planters with lush greenery on both sides of the escalator)
("object"{{tuple_delimiter}}PLANTERS{{tuple_delimiter}}various)
("object"{{tuple_delimiter}}GREENERY{{tuple_delimiter}}lush)
("object"{{tuple_delimiter}}FLOOR{{tuple_delimiter}}polished with colored tiles)
("object"{{tuple_delimiter}}MAN{{tuple_delimiter}}ascending the left escalator)
("object"{{tuple_delimiter}}SHOPS{{tuple_delimiter}}some open and some closed)
("object"{{tuple_delimiter}}SECOND FLOOR{{tuple_delimiter}}shops appear to be open and closed)
("object"{{tuple_delimiter}}CEILING{{tuple_delimiter}}has recessed lighting)
("object"{{tuple_delimiter}}LIGHTING{{tuple_delimiter}}recessed)
("object"{{tuple_delimiter}}STONE COLUMNS{{tuple_delimiter}}several)
("relationship"{{tuple_delimiter}}ESCALATORS{{tuple_delimiter}}INDOOR MALL{{tuple_delimiter}}The escalators are part of the indoor mall{{tuple_delimiter}}9)
("relationship"{{tuple_delimiter}}PLANTERS{{tuple_delimiter}}MALL{{tuple_delimiter}}The planters are part of the mall{{tuple_delimiter}}8)
("relationship"{{tuple_delimiter}}GREENERY{{tuple_delimiter}}PLANTERS{{tuple_delimiter}}The greenery is in the planters{{tuple_delimiter}}9)
("relationship"{{tuple_delimiter}}MAN{{tuple_delimiter}}ESCALATORS{{tuple_delimiter}}The man is ascending the left escalator{{tuple_delimiter}}7)
("relationship"{{tuple_delimiter}}SHOPS{{tuple_delimiter}}SECOND FLOOR{{tuple_delimiter}}The shops are on the second floor{{tuple_delimiter}}8)
("relationship"{{tuple_delimiter}}LIGHTING{{tuple_delimiter}}CEILING{{tuple_delimiter}}The recessed lighting is part of the ceiling{{tuple_delimiter}}8)
("relationship"{{tuple_delimiter}}STONE COLUMNS{{tuple_delimiter}}INDOOR MALL{{tuple_delimiter}}The stone columns are part of the indoor mall{{tuple_delimiter}}8)
VLM List:

("object"{{tuple_delimiter}}SHOPPING MALL{{tuple_delimiter}}indoor)
("object"{{tuple_delimiter}}SHOPPING MALL{{tuple_delimiter}}at night)
("object"{{tuple_delimiter}}ESCALATOR{{tuple_delimiter}}long)
("object"{{tuple_delimiter}}ESCALATOR{{tuple_delimiter}}brightly lit)
("object"{{tuple_delimiter}}CENTER OF THE MALL{{tuple_delimiter}}location of escalator)
("object"{{tuple_delimiter}}POTTED PLANTS{{tuple_delimiter}}several)
("object"{{tuple_delimiter}}SPACE{{tuple_delimiter}}greenery)
("object"{{tuple_delimiter}}BENCHES{{tuple_delimiter}}multiple)
("object"{{tuple_delimiter}}BENCHES{{tuple_delimiter}}providing seating options)
("object"{{tuple_delimiter}}MALL{{tuple_delimiter}}well-lit)
("object"{{tuple_delimiter}}MALL{{tuple_delimiter}}inviting)
("object"{{tuple_delimiter}}MALL{{tuple_delimiter}}dark)
("object"{{tuple_delimiter}}WOMAN{{tuple_delimiter}}beautiful)
("relationship"{{tuple_delimiter}}ESCALATOR{{tuple_delimiter}}SHOPPING MALL{{tuple_delimiter}}The escalator is a feature within the shopping mall{{tuple_delimiter}}9)
("relationship"{{tuple_delimiter}}ESCALATOR{{tuple_delimiter}}CENTER OF THE MALL{{tuple_delimiter}}The escalator is located in the center of the mall{{tuple_delimiter}}9)
("relationship"{{tuple_delimiter}}POTTED PLANTS{{tuple_delimiter}}ESCALATOR{{tuple_delimiter}}The potted plants are surrounding the escalator{{tuple_delimiter}}8)
("relationship"{{tuple_delimiter}}POTTED PLANTS{{tuple_delimiter}}SPACE{{tuple_delimiter}}The potted plants add greenery to the space{{tuple_delimiter}}7)
("relationship"{{tuple_delimiter}}BENCHES{{tuple_delimiter}}SHOPPING MALL{{tuple_delimiter}}The benches are placed throughout the shopping mall{{tuple_delimiter}}8)
("relationship"{{tuple_delimiter}}BENCHES{{tuple_delimiter}}ESCALATOR{{tuple_delimiter}}Some benches are located near the escalator{{tuple_delimiter}}7)
("relationship"{{tuple_delimiter}}BENCHES{{tuple_delimiter}}SHOPPING MALL{{tuple_delimiter}}The benches provide seating options for shoppers in the mall{{tuple_delimiter}}8)
("relationship"{{tuple_delimiter}}MALL{{tuple_delimiter}}SHOPPING MALL{{tuple_delimiter}}The overall atmosphere of the mall is well-lit and inviting{{tuple_delimiter}}8)
Analysis:

Entry 2 in VLM List: ("object"{{tuple_delimiter}}SHOPPING MALL{{tuple_delimiter}}at night)
The attribute "at night" is not mentioned in the GT List. Since "SHOPPING MALL" corresponds to "INDOOR MALL" in the GT List, and the object exists, the incorrect attribute "at night" counts as a hallucination.
Entry 5 in VLM List: ("object"{{tuple_delimiter}}CENTER OF THE MALL{{tuple_delimiter}}location of escalator)
The object "CENTER OF THE MALL" does not exist in the GT List. This counts as one hallucination for the incorrect object "CENTER OF THE MALL".
Entries 8 and 9 in VLM List: ("object"{{tuple_delimiter}}BENCHES{{tuple_delimiter}}multiple), ("object"{{tuple_delimiter}}BENCHES{{tuple_delimiter}}providing seating options)
The object "BENCHES" does not exist in the GT List. Regardless of multiple entries, it counts as one hallucination for the incorrect object "BENCHES".
Entry 12 in VLM List: ("object"{{tuple_delimiter}}MALL{{tuple_delimiter}}dark)
The attribute "dark" contradicts the GT List, which describes the mall as illuminated with recessed lighting and illuminated escalators. The incorrect attribute "dark" counts as a hallucination.
Entry 13 in VLM List: ("object"{{tuple_delimiter}}WOMAN{{tuple_delimiter}}beautiful)
The object "WOMAN" does not exist in the GT List. This counts as one hallucination for the incorrect object "WOMAN".
Entry 15 in VLM List: ("relationship"{{tuple_delimiter}}ESCALATOR{{tuple_delimiter}}CENTER OF THE MALL{{tuple_delimiter}}The escalator is located in the center of the mall{{tuple_delimiter}}9)
"CENTER OF THE MALL" is an incorrect object already counted. This relationship involves an incorrect object, so it does not count separately.
Entries 18, 19, and 20 in VLM List: Relationships involving "BENCHES"
"BENCHES" is an incorrect object already counted. Relationships involving "BENCHES" do not count separately.
Incorrect Serial Numbers: 2, 5, 8, 12, 13

Your task is to compare the following lists and provide the incorrect serial numbers as per the instructions above.

GT List:

{gt_list}

VLM List:

{vlm_list}"""

OMISSION_PROMPT = """
-Goal-

Given two lists of objects, attributes, and relationships extracted from a ground truth (GT) caption and a Vision-Language Model (VLM) caption—both numbered—compare the GT list to the VLM list to identify any missing objects, attributes, or relationships in the VLM caption. A missing object, attribute, or relationship is one that is present in the GT list but not in the VLM list. Importantly, use your language understanding to assess whether objects, attributes, and relationships convey the same meaning, even if expressed differently.

Instructions

Input Data:

You will be provided with two numbered lists:

GT List: The ground truth caption's list of objects, attributes, and relationships.
VLM List: The VLM caption's list of objects, attributes, and relationships.
Comparison Process:

Step 1: For each entry in the GT list, determine if it exists in the VLM list.

For Objects:
If an object in the GT list matches an object in the VLM list (considering synonyms and similar expressions), proceed to compare its attributes and relationships.
If an object in the GT list does not exist in the VLM list, classify it as a missing object.
Important: If a missing object appears multiple times in the GT list (with different attributes or relationships), it counts as one missing object.
For Attributes:
An attribute in the GT list matches the VLM list if there is an object with the same name (or similar) and the attribute conveys the same meaning as an attribute of that object in the VLM list, even if the wording is different.
If an object exists in both lists but has attributes in the GT list that are not present in the VLM list, classify each missing attribute as a missing attribute.
Each missing attribute counts as one missing element.
For Relationships:
A relationship in the GT list matches the VLM list if there is a relationship with the same source object and target object, and the relationship description conveys the same meaning as a relationship in the VLM list, even if the wording is different.
If a relationship in the GT list involves a missing object (one not present in the VLM list), it is considered part of the missing information for that object and does not count separately.
If a relationship involves objects that are present in both lists but is missing from the VLM list, classify it as a missing relationship.
Each missing relationship counts as one missing element, unless it involves a missing object already counted.
Step 2: Compile the list of missing elements.

Objects:
List each missing object (counts as one missing element per object, regardless of how many times it appears).
Attributes:
List each missing attribute separately (each counts as a separate missing element).
Relationships:
List each missing relationship separately (each counts as a separate missing element), unless it involves a missing object already counted.
Output Instructions:

Analysis:
Provide a brief analysis explaining which entries are missing and why, following the format:

**Analysis:**

- **Entry [Serial Number] in GT List:** [Entry Details]
  - [Explanation of why it's missing]
Missing Serial Numbers:
Collect all the serial numbers from the GT list that correspond to missing objects (one per missing object), missing attributes, and missing relationships (excluding those involving already counted missing objects).
Present them in a single list, in numerical order, separated by commas.
Example: Missing Serial Numbers: 3, 6, 9
Do not include any additional explanations or text in the output.
Notes:

Semantic Matching:
Use your language understanding to determine whether objects, attributes, or relationships in the GT list and VLM list convey the same meaning.
Minor variations in wording or phrasing that convey the same meaning should be considered a match.
Only consider an object, attribute, or relationship missing if it is present in the GT list but not represented in the VLM list, or if the meaning significantly differs.
Case Sensitivity:
Object names and attributes are case-insensitive for matching purposes.
Ignore Serial Numbers in VLM List:
Use the serial numbers only from the GT list when reporting missing entries.
Example:

GT List:

("object"{{tuple_delimiter}}INDOOR MALL{{tuple_delimiter}}has three illuminated escalators)
("object"{{tuple_delimiter}}ESCALATORS{{tuple_delimiter}}illuminated)
("object"{{tuple_delimiter}}MALL{{tuple_delimiter}}various planters with lush greenery on both sides of the escalator)
("object"{{tuple_delimiter}}PLANTERS{{tuple_delimiter}}various)
("object"{{tuple_delimiter}}GREENERY{{tuple_delimiter}}lush)
("object"{{tuple_delimiter}}FLOOR{{tuple_delimiter}}polished with colored tiles)
("object"{{tuple_delimiter}}MAN{{tuple_delimiter}}ascending the left escalator)
("object"{{tuple_delimiter}}SHOPS{{tuple_delimiter}}some open and some closed)
("object"{{tuple_delimiter}}SECOND FLOOR{{tuple_delimiter}}shops appear to be open and closed)
("object"{{tuple_delimiter}}CEILING{{tuple_delimiter}}has recessed lighting)
("object"{{tuple_delimiter}}LIGHTING{{tuple_delimiter}}recessed)
("object"{{tuple_delimiter}}STONE COLUMNS{{tuple_delimiter}}several)
("relationship"{{tuple_delimiter}}ESCALATORS{{tuple_delimiter}}INDOOR MALL{{tuple_delimiter}}The escalators are part of the indoor mall{{tuple_delimiter}}9)
("relationship"{{tuple_delimiter}}PLANTERS{{tuple_delimiter}}MALL{{tuple_delimiter}}The planters are part of the mall{{tuple_delimiter}}8)
("relationship"{{tuple_delimiter}}GREENERY{{tuple_delimiter}}PLANTERS{{tuple_delimiter}}The greenery is in the planters{{tuple_delimiter}}9)
("relationship"{{tuple_delimiter}}MAN{{tuple_delimiter}}ESCALATORS{{tuple_delimiter}}The man is ascending the left escalator{{tuple_delimiter}}7)
("relationship"{{tuple_delimiter}}SHOPS{{tuple_delimiter}}SECOND FLOOR{{tuple_delimiter}}The shops are on the second floor{{tuple_delimiter}}8)
("relationship"{{tuple_delimiter}}LIGHTING{{tuple_delimiter}}CEILING{{tuple_delimiter}}The recessed lighting is part of the ceiling{{tuple_delimiter}}8)
("relationship"{{tuple_delimiter}}STONE COLUMNS{{tuple_delimiter}}INDOOR MALL{{tuple_delimiter}}The stone columns are part of the indoor mall{{tuple_delimiter}}8)
VLM List:

("object"{{tuple_delimiter}}SHOPPING MALL{{tuple_delimiter}}indoor)
("object"{{tuple_delimiter}}SHOPPING MALL{{tuple_delimiter}}welcoming)
("object"{{tuple_delimiter}}ESCALATORS{{tuple_delimiter}}brightly lit)
("object"{{tuple_delimiter}}PLANTERS{{tuple_delimiter}}several)
("object"{{tuple_delimiter}}GREENERY{{tuple_delimiter}}lush)
("object"{{tuple_delimiter}}FLOOR{{tuple_delimiter}}polished with tiles)
("object"{{tuple_delimiter}}SHOPS{{tuple_delimiter}}open and closed)
("object"{{tuple_delimiter}}LIGHTING{{tuple_delimiter}}bright)
("relationship"{{tuple_delimiter}}ESCALATORS{{tuple_delimiter}}SHOPPING MALL{{tuple_delimiter}}The escalators are part of the shopping mall{{tuple_delimiter}}9)
("relationship"{{tuple_delimiter}}PLANTERS{{tuple_delimiter}}SHOPPING MALL{{tuple_delimiter}}The planters are part of the mall{{tuple_delimiter}}8)
("relationship"{{tuple_delimiter}}GREENERY{{tuple_delimiter}}PLANTERS{{tuple_delimiter}}The greenery is in the planters{{tuple_delimiter}}9)
("relationship"{{tuple_delimiter}}LIGHTING{{tuple_delimiter}}MALL{{tuple_delimiter}}The bright lighting is part of the mall{{tuple_delimiter}}8)
Analysis:

Entry 7 in GT List: ("object"{{tuple_delimiter}}MAN{{tuple_delimiter}}ascending the left escalator)
The object "MAN" is missing from the VLM List. This counts as one missing object.
Entry 10 in GT List: ("object"{{tuple_delimiter}}CEILING{{tuple_delimiter}}has recessed lighting)
The object "CEILING" is missing from the VLM List. This counts as one missing object.
Entry 11 in GT List: ("object"{{tuple_delimiter}}LIGHTING{{tuple_delimiter}}recessed)
The VLM List has "LIGHTING" with attribute "bright" but does not mention "recessed". The attribute "recessed" is missing.
Entry 12 in GT List: ("object"{{tuple_delimiter}}STONE COLUMNS{{tuple_delimiter}}several)
The object "STONE COLUMNS" is missing from the VLM List. This counts as one missing object.
Entry 16 in GT List: ("relationship"{{tuple_delimiter}}MAN{{tuple_delimiter}}ESCALATORS{{tuple_delimiter}}The man is ascending the left escalator{{tuple_delimiter}}7)
Since "MAN" is a missing object, this relationship does not count separately.
Entry 18 in GT List: ("relationship"{{tuple_delimiter}}LIGHTING{{tuple_delimiter}}CEILING{{tuple_delimiter}}The recessed lighting is part of the ceiling{{tuple_delimiter}}8)
The relationship between "LIGHTING" and "CEILING" is missing because "CEILING" is a missing object. This does not count separately.
Entry 19 in GT List: ("relationship"{{tuple_delimiter}}STONE COLUMNS{{tuple_delimiter}}INDOOR MALL{{tuple_delimiter}}The stone columns are part of the indoor mall{{tuple_delimiter}}8)
Since "STONE COLUMNS" is a missing object, this relationship does not count separately.
Missing Serial Numbers: 7, 10, 11, 12

Your task is to compare the following lists and provide the missing serial numbers as per the instructions above.

GT List:

{gt_list}

VLM List:

{vlm_list}"""


def extract_number(dictionary):
    match = re.search(r'sa_(\d+).jpg', dictionary['image'])
    return int(match.group(1)) if match else None
class GPT4V:
    def __init__(self):
        self.url = '<url>'
        self.configs = [
            {
                'appid': "<appid>",
                'appkey': "<appkey>",
                'source': "webpage_text_gpt4v",
            },
        ]

    def calcAuthorization(self, config):
        source = config['source']
        appkey = config['appkey']
        timestamp = int(time.time())
        signStr = "x-timestamp: %s\nx-source: %s" % (timestamp, source)
        sign = hmac.new(appkey.encode('utf-8'), signStr.encode('utf-8'), hashlib.sha256).digest()
        return sign.hex(), timestamp

    def __call__(self, messages):
        config = random.choice(self.configs)
        appid = config['appid']
        source = config['source']
        auth, timestamp = self.calcAuthorization(config)
        headers = {
            "Content-Type": "application/json",
            "x-appid": appid,
            "x-source": source,
            "x-timestamp": str(timestamp),
            "x-authorization": auth,
        }
        payload = {
            "model": "gpt-4o",
            "messages": messages,
            "max_tokens": 4096
        }
        response = requests.post(self.url, json=payload, headers=headers)
        response_text = json.loads(response.text)
        return response_text['response']

def generate_response(input_text):
    gpt_instance = GPT4V()
    messages = [
        {"role": "user", "content": ENTITY_RELATIONSHIPS_GENERATION_PROMPT.format(input_text=input_text)},
    ]
    response = gpt_instance(messages)
    return response

def analyze_hallucination(response_gt, response_vlm):
    gpt_instance = GPT4V()
    messages = [
        {"role": "user", "content": HALL_PROMPT.format(gt_list=response_gt, vlm_list=response_vlm)},
    ]
    hallucination_analysis_list = gpt_instance(messages)
    return hallucination_analysis_list

def analyze_omission(response_gt, response_vlm):
    gpt_instance = GPT4V()
    messages = [
        {"role": "user", "content": OMISSION_PROMPT.format(gt_list=response_gt, vlm_list=response_vlm)},
    ]
    omission_caption_analysis_list = gpt_instance(messages)
    return omission_caption_analysis_list

def process_single_image(args_tuple):
    idx, image_id, gt_caption, vlm_caption, save_path = args_tuple
    single_eval = dict()
    single_eval['image'] = image_id
    single_eval['gt_caption'] = gt_caption
    single_eval['vlm_caption'] = vlm_caption

    try:
        response_gt = generate_response(gt_caption)
        response_vlm = generate_response(vlm_caption)

        hallucination_analysis_list = analyze_hallucination(response_gt, response_vlm)
        omission_caption_analysis_list = analyze_omission(response_gt, response_vlm)

        pattern = re.compile(r'(\d+)\.')
        matches_gt = pattern.findall(response_gt)
        matches_vlm = pattern.findall(response_vlm)
        single_eval['response_gt'] = response_gt
        single_eval['response_vlm'] = response_vlm
        single_eval['hallucination_analysis_list'] = hallucination_analysis_list
        single_eval['omission_caption_analysis_list'] = omission_caption_analysis_list
        single_eval['gt_num_concepts'] = len(matches_gt)
        single_eval['vlm_num_concepts'] = len(matches_vlm)

        index = hallucination_analysis_list.rfind('Serial Numbers:')
        incorrect_numbers_line = hallucination_analysis_list[index:]
        outputs_hallucination_list = [
            int(num) for num in re.findall(r'\d+', incorrect_numbers_line)
        ]
        hallusion_concepts_num = len(outputs_hallucination_list)
        single_eval['hallusion_concepts_idx'] = outputs_hallucination_list
        single_eval['vlm_hallusion_concepts_num'] = hallusion_concepts_num

        index = omission_caption_analysis_list.rfind('Serial Numbers:')
        missing_numbers_line = omission_caption_analysis_list[index:]
        gt_omission_idx_list = [
            int(num) for num in re.findall(r'\d+', missing_numbers_line)
        ]
        single_eval['gt_omission_concepts_idx'] = gt_omission_idx_list
        single_eval['gt_omission_concepts_num'] = len(gt_omission_idx_list)

        if single_eval['vlm_num_concepts'] > 0:
            single_eval['halusion_score'] = 1.0 - single_eval['vlm_hallusion_concepts_num'] / single_eval['vlm_num_concepts']
        else:
            single_eval['halusion_score'] = 0.0

        if single_eval['gt_num_concepts'] > 0:
            single_eval['quality_score'] = 1.0 - single_eval['gt_omission_concepts_num'] / single_eval['gt_num_concepts']
        else:
            single_eval['quality_score'] = 0.0

        if (single_eval['halusion_score'] + single_eval['quality_score']) > 0:
            single_eval['f_score'] = 2.0 / (
                1.0 / single_eval['halusion_score'] + 1.0 / single_eval['quality_score']
            )
        else:
            single_eval['f_score'] = 0.0

    except Exception as e:
        print(f"Error evaluating image {image_id} at index {idx}: {e}")

    with open(save_path, "a") as f:
        f.write(json.dumps(single_eval) + '\n')

    time.sleep(2)
    return single_eval

def process_image_wrapper(args):
    return process_single_image(args)

def main(args):
    cap_file = args.cap_file
    cap_result = args.cap_file_result

    with open(cap_file, 'r') as file:
        caption_annotations = json.load(file)

    caption_results = {}
    with open(cap_result, 'r') as file:
        for line in file:
            data = json.loads(line)
            image_id = data['image']
            caption = data['caption']
            caption_results[image_id] = caption

    caption_annotations_dict = {}
    for item in caption_annotations:
        image_id = item['image']
        caption = item['caption']
        caption_annotations_dict[image_id] = caption

    existing_results = set()
    try:
        with open(args.save_path, 'r') as f:
            for idx, line in enumerate(f):
                # import pdb; pdb.set_trace()
                data = json.loads(line)
                # print(idx)
                existing_results.add(data['image'])
    except FileNotFoundError:
        pass
    # except:
    #     import pdb; pdb.set_trace()
    #     pass
    eval_annotation = []
    image_ids = list(caption_annotations_dict.keys())
    max_eval = 1000
    image_ids = [id for id in image_ids[:max_eval] if id not in existing_results]

    args_list = []
    for idx, image_id in enumerate(image_ids):
        gt_caption = caption_annotations_dict[image_id]
        vlm_caption = caption_results.get(image_id, "")
        args_list.append((idx, image_id, gt_caption, vlm_caption, args.save_path))

    with multiprocessing.Pool() as pool:
        for _ in tqdm(pool.imap_unordered(process_image_wrapper, args_list), total=len(args_list)):
            pass

    with open(args.save_path, 'r') as f:
        results = [json.loads(line) for line in f]

    total_vlm_hallusion_concepts_num = sum(
        item.get('vlm_hallusion_concepts_num', 0) for item in results if 'vlm_hallusion_concepts_num' in item
    )
    total_vlm_num_concepts = sum(
        item.get('vlm_num_concepts', 0) for item in results if 'vlm_num_concepts' in item
    )
    total_gt_omission_concepts_num = sum(
        item.get('gt_omission_concepts_num', 0) for item in results if 'gt_omission_concepts_num' in item
    )
    total_gt_num_concepts = sum(
        item.get('gt_num_concepts', 0) for item in results if 'gt_num_concepts' in item
    )

    if total_vlm_num_concepts > 0:
        average_halusion_score = 1.0 - total_vlm_hallusion_concepts_num / total_vlm_num_concepts
    else:
        average_halusion_score = 0.0

    if total_gt_num_concepts > 0:
        average_quality_score = 1.0 - total_gt_omission_concepts_num / total_gt_num_concepts
    else:
        average_quality_score = 0.0

    if (average_halusion_score + average_quality_score) > 0:
        f_score = 2.0 / (
            1.0 / average_halusion_score + 1.0 / average_quality_score
        )
    else:
        f_score = 0.0

    summary = {
        'hallucination_score': average_halusion_score,
        'recall_score': average_quality_score,
        'f_score': f_score
    }

    with open(args.save_path, "a") as f:
        f.write(json.dumps(summary) + '\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--cap_file",
        type=str,
        default='/apdcephfs/csp/mmvision/home/chencong/code/CongEvaluator/data/FinalBench/annotation.json',
        help="Ground truth caption file"
    )
    parser.add_argument(
        "--cap_file_result",
        type=str,
        default='/apdcephfs/csp/mmvision/home/chencong/code/CongEvaluator/data/FinalBench/results/llava/RLAIF-V-7B/llava_our_bench.jsonl',
        help="VLM caption results file"
    )
    parser.add_argument(
        "--model_dtype",
        type=str,
        default='bf16',
        help="Model data type"
    )
    parser.add_argument(
        "--save_path",
        type=str,
        default="/apdcephfs/csp/mmvision/home/chencong/code/CongEvaluator/data/FinalBench/results/llava/RLAIF-V-7B/eval_llava.jsonl",
        help="Path to save results"
    )
    args = parser.parse_args()

    main(args)