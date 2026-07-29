from openai import OpenAI


#
#
# For tasks like extractive reasoning from tabular data
# wwe should use a low temperature, typically temperature=0.0 to 0.3, to ensure deterministic and accurate outputs.
#
# temperature=0.0: Best for tasks requiring precision and consistency.
#
# temperature=0.7+: Used for creative tasks, not ideal for fact-based answers.



def get_completion(prompt, model="gpt-4o", temperature=0.15, n=1):
    if n < 1 or n > 5:
        raise ValueError("Parameter 'n' must be between 1 and 3.")

    client = OpenAI()
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        n=n,
    )

    if n == 1:
        return response.choices[0].message.content
    else:
        return [choice.message.content for choice in response.choices]

###################################################################

######################################################  agent with previous agents  #######################################################################


def prompt_agent_follow(title: str, question: str, headers: list, total_rows: int, outputs_previous: str,
                        subtable: list, number_agent: int, row_rank: list):
    return f"""You are AGENT_FOL_{number_agent}, responsible for analyzing the next split (subtable) of a full table. 
      Your task is to extract key insights and provide hints to AGENT_FOL_{number_agent + 1}, (who holds information about the next subtable) 
      to answer questions about the FULL TABLE.

      INSTRUCTIONS:
      1. Analyze this subtable:
         - Title: {title}
         - HEADERS: {headers}
         - QUESTION: {question}
         - TOTAL ROWS IN FULL TABLE: {total_rows}
         - YOUR SUBTABLE :{subtable}
         - LIST of your rows number according to the full table : {row_rank}
      2. Analyse previous output of previuos AGENT_FOL:
         - output AGENT_FOL_{number_agent - 1} : {outputs_previous}
      3. answer the question in your subtable / if you can 
      4. think step by step , take your time , creticate your raisoning untill being sure about your outputs to AGENT_FOL_{number_agent + 1}
      5.OUTPUTS:
       - previous answer (AGENT_FOL_{number_agent - 1} )
       - present answer (your answer)
       - all information that can help AGENT_FOL_{number_agent + 1} to solve the question
       """


def prompt_agent_synthesis(title: str, question: str, headers: list, total_rows: int, outputs: list):
    return f"""You are AGENT_SYN a Synthesis expert for tables (2D), responsible for analyzing ,synthesising and answering question using informations about each subtable . 
     Your task is to COMBINE answers of each subtable, information from AGENTS  to answer the question on the FULL TABLE, the full table is a group of subtables.

     INSTRUCTIONS:
    1. Analyse your inputs :
     -Title: {title}
     -HEADERS: {headers}
     -QUESTION: {question}
     -TOTAL ROWS IN FULL TABLE: {total_rows}
    2. analyse AGENTS outputs (list format [AGENT_COL_0:output,AGENT_COL_2:output2,..ect] ):
      - outputs={outputs}
      - iterate over agents and analyse their answers and there informations.
    3. collect all information and answers provided by AGENTS.
    4. Review the question 
    5. Generate the FINAL ANSWER  by combining AGENTS's outputs with your analysis (without extra information, output all numbers as digits):
      -creticate your raisoning untill being sure about your final answer about the full table
    """
    # -output the final answer to the question  between  ##  (e.g the answer is #...#)
    #       -Answer concisely. Give only the exact word, number, name, or short phrase.
    #        No explanations. No full sentences. No punctuation unless required (e.g., years or units)


def prompt_answer_refiner(question: str, response: str):
    return f"""You are an answer refiner. Given a question and an "answer extra info" field containing detailed information, your task is to extract a concise, normalized answer:

-INSTRUCTIONS:
1. analyse the question : {question}.
2. analyse the answer (with extra info): {response}.
3. refine the answer to be direct concise like human answer and refer to the question appellation (names ,palces, persons )
-guidelines
If the answer is a proper noun (e.g., name of a place or person), return the one mentioned here {question} :.

If multiple relevant entities are listed in the extra info (e.g., towns, people), include them all, separated by commas and in lowercase.

Keep the answer concise and free of unnecessary words or formatting.
Follow these examples:

question: "who lived longer, kading or kaufman?"
answer extra info: "By combining the information from all agents Charles A. Kading lived longer"
step by step thinking, in the question they mentioned only comparison between to  names kading or kaufman so
the refine answer is the name mentiond in the question
answer: "kading"

question: "what was the name of the first national park which was established in 1872?"
answer extra info: "By combining the information from all agents the Yellowstone National Park is the first"
step by step thinking , from the question we know that the question is about a national park , so we dont need to add this 
information in the answer so .
answer: "yellowstone"

question: "what ghost towns are in the same country as new york?"
answer extra info: "new york, loss angelos, california"
step by step thinking, the question is a comparison between towns and the town new york, so we dont need to mention 
new york also in the answer so
answer: "loss angelos,california"

Now, given the following input, return only the refined answer:
question: {question}
answer extra info: {response}
step by step thinking
answer:

"""


## -always format list answer (multipule elements) using only comas, without conjuctions like "and" or any punctuation like periods.

#
#
#  INSTRUCTIONS:
# 1. Analyse your inputs :
#  -ORIGINAL QUESTION: {question}
#  -HEADERS: {headers}
#  -TOTAL ROWS IN FULL TABLE: {total_rows}
# 2. analyse AGENTS outputs (list format [AGENT_COL_0:output,AGENT_COL_2:output2,..ect] ):
#   - outputs={outputs}
#   - iterate over agents and analyse their answers and there informations
# 3. synthesis all information and answers
# 4. use all information provided by AGENTS
# 5. Generate the FINAL ANSWER  by combining AGENTS's outputs with your analysis :
#  _ FINAL ANSWER (without extra information, Output all numbers as digits)
# """


def prt_answer_context(question, headers, top_rows):
    # Format headers
    headers_str = ", ".join(f'"{h}"' for h in headers)

    # Format rows
    rows_str = "[\n" + "\n".join(["  " + str(row) for row in top_rows]) + "\n]"

    prompt = f"""You are a table-to-text converter.
I will give you:
- A natural language question about a table.
- The headers of the table.
- The top most relevant rows (based on semantic similarity to the question).

Your task is to:
1. Convert each relevant row into a clear, human-readable sentence.
2. Focus on the values relevant to answering the question.
3. Return a short paragraph with these sentences that can be used as context to help answer the question.

---
Question:
{question}

Headers:
[{headers_str}]

Top 3 Rows:
{rows_str}
"""

    return prompt


#
#
#
# def prompt_agent_follow(title: str,question: str, headers: list, suppor_facts: str,total_rows: int,outputs_previous: str,subtable: list, number_agent: int):
#     return f"""You are AGENT_FOL_{number_agent}, responsible for analyzing the next split (subtable) of a full table.
#       Your task is to extract key insights and provide hints to AGENT_FOL_{number_agent + 1}, (who holds information about the next subtable)
#       to answer questions about the FULL TABLE.
#
#       INSTRUCTIONS:
#       1. Analyze this subtable:
#          - Title: {title}
#          - HEADERS: {headers}
#          - QUESTION: {question}
#          - SUPPORTIVE FACTS (generated Context about the answer):{suppor_facts}
#          - TOTAL ROWS IN FULL TABLE: {total_rows}
#          - YOUR SUBTABLE :{subtable}
#       2. Analyse previous output of previuos AGENT_FOL:
#          - output AGENT_FOL_{number_agent-1} : {outputs_previous}
#       3. answer the question in your subtable / if you can
#       4. think step by step , take your time , creticate your raisoning untill being sure about your outputs to AGENT_FOL_{number_agent + 1}
#       5.OUTPUTS:
#        - previous answer (AGENT_FOL_{number_agent - 1} )
#        - present answer (your answer)
#        - all information that can help AGENT_FOL_{number_agent + 1} to solve the question
#        """


def extract_relevant_table_elements(question, headers, top_rows):
    return f"""You are a data reasoning assistant.  
You will be given:
- A natural language question about a table.  
- The headers of the table.  
- A few top relevant rows based on semantic similarity.  

Your task is to:
1. Determine whether the question requires examining specific **columns** (headers) or comparing entire **rows**.  

- If the question requires **analyzing or locating information inside specific columns**, or selecting a column that holds relevant data (e.g., "which column has population info?" or "what is the status field?"), it is **column-dependent**.  
- If the question requires **comparing or selecting specific rows** (e.g., "which player scored more?" or "who has the highest total?"), it is **row-dependent**.  
- all questions about ordering (e.g what is the first .. ?, what is the last .. ?, what is in the middle .. ? ..) are column_dependent
2. Based on this, output:
- Only the **relevant headers**, if column-dependent.  
- Only the **relevant rows**, if row-dependent.  

Return your answer in **list  format**:

  -relevant_headers: [ ... ]
  -relevant_rows: [ ... ]

Few shot examples
Example 1:
Question: Does Pat or John have the highest total?
Headers: ["name", "league", "fa cup", "league cup", "jp trophy", "total"]
Top Rows: [
  ["john o'flynn", "4", "0", "3", "0", "20"],
  ["pat baldwin", "-01", "0", "0", "0", "8"],
  ["jake gosling", "22", "0", "0", "0", "21"]
]
Thinking : step by step pat and jhon they are mentioned directly in the rows so its a row dependent question , and there is
the world highest total it means its columns dependent 
Output:

  -relevant_headers: ["name", "total"],
  -relevant_rows: [
    ["john o'flynn", "4", "0", "3", "0", "20"],
    ["pat baldwin", "-01", "0", "0", "0", "8"]
  ]


Example 2:
Question: Which town has the top remaining population to this date?
Headers: ["town name", "county", "established", "disestablished", "current status", "remarks"]
Top Rows: [
  ["white cloud", "doniphan county", "1856", "", "2008 estimated population of 227", ""],
  ["ray", "pawnee county", "", "", "most of the houses were demolished or moved in the 1950s...", ""]
]
Thinking : step by step there is no specific name of town mentioned in the question , so no row mentioned so not row dependent
, so we need to iterate over all towns , it means a column dependent

Output:

  "relevant_headers": ["town name", "current status"],
  "relevant_rows": []
  
Example 3:
Question: who was, were the oldest winner(s) of big brother (uk)?
Headers: ['series', 'name', 'age', 'hometown', 'occupation', 'status']
Top Rows: [
  ['bb1', 'craig phillips', '28', 'liverpool', 'builder', '1st - winner'],
  ['bb2', 'brian dowling', '22', 'county kildare', 'air steward', '1st - winner'],
  ['bb3', 'kate lawler', '22', 'london', 'technical support administrator', '1st - winner']
]
Thinking : step by step there is no specific name mentioned in the question so not row dependent , but we need to iterate over all name , age, and status
to get the answer so its a column dependent

Output:

  -relevant_headers: ["name", "age", "status"],
  -relevant_rows: [
    []
  ] 
Example 4:
Question: what is the first name listed?  
Headers: ['name', 'location', 'date established', 'area', 'description']  
Top Rows: [
  ['denali', 'alaska63°20′n 150°30′w63.33°n 150.50°w', 'february 26, 1917', '4,740,911.72 acres (19,185.8\\km2)', 'centered around the mount mckinley, the tallest mountain in north america, denali is serviced by a single road leading to wonder lake. mckinley and other peaks of the alaska range are covered with long glaciers and boreal forest. wildlife includes grizzly bears, dall sheep, caribou, and gray wolves.'],
  ['congaree', 'south carolina33°47′n 80°47′w / 33.78°n 80.78°w', 'november 10, 2003', '26,545.86 acres (107.4\\km2)', 'on the congaree river, this park is the largest portion of old-growth floodplain forest left in north america. some of the trees are the tallest in the eastern us, and the boardwalk loop is an elevated walkway through the swamp.'],
  ['haleakalā', 'hawaii20°43′n 156°10′w20.72°n 156.17°w', 'august 1, 1916', '29,093.67 acres (117.7\\km2)', "the haleakalā volcano on maui has a very large crater with many cinder cones, hosmer's grove of alien trees, and the native hawaiian goose. the kipahulu section has numerous pools with freshwater fish. this national park has the greatest number of endangered species."]
]

Thinking: The question asks for the "first name listed," which means we are interested in the order of the rows and not a specific name in the row . This makes the question culumn-dependent, as it requires examining the first row (not specific name in the row ) to find the first name listed.

Output:

  -relevant_headers: ["name"],
  -relevant_rows: []
  
  
Question :{question}
Headers :{headers}
Top Rows:{top_rows}
Thinking: step by step ...
Output:
  "relevant_headers": [...],
  "relevant_rows": [...]
"""
