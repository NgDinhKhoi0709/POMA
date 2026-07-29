import os
from openai import OpenAI
import os


API_KEY = ''' '''
os.environ['OPENAI_API_KEY'] = API_KEY

client = OpenAI(
    api_key=os.environ['OPENAI_API_KEY'],  # this is also the default, it can be omitted
)



def get_completion(prompt, model="gpt-4o", temperature=0.2, n=1):
    if n < 1 or n > 5:
        raise ValueError("Parameter 'n' must be between 1 and 3.")

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


######################################################  agent with previous agents  #######################################################################


def prompt_agent_follow_tabfact(title: str, question: str, headers: list, total_rows: int, outputs_previous: str,
                        subtable: list, number_agent: int, row_rank: list):
    return f"""You are AGENT_FOL_{number_agent}, responsible for analyzing the next split (subtable) of a full table. 
      Your task is to extract key insights and provide hints to AGENT_FOL_{number_agent + 1}, (who holds information about the next subtable) 
      to verify whether the provided claims are true or false about the FULL TABLE.
      
      INSTRUCTIONS:
      1. Analyze this subtable:
         - Title: {title}
         - HEADERS: {headers}
         - CLAIM: {question}
         - TOTAL ROWS IN FULL TABLE: {total_rows}
         - YOUR SUBTABLE :{subtable}
         - LIST of your rows number according to the full table : {row_rank}
      2. Analyse previous output of previuos AGENT_FOL:
         - output AGENT_FOL_{number_agent - 1} : {outputs_previous}
      3. verify and explain whether the provided claims are true or false in your subtable / if you can 
      4. think step by step , take your time , creticate your raisoning untill being sure about your outputs to AGENT_FOL_{number_agent + 1}
      5.OUTPUTS:
       - previous explanation (AGENT_FOL_{number_agent - 1} )
       - present explanation (your explanation)
       - all information that can help AGENT_FOL_{number_agent + 1} to verify the claims
       """


def prompt_agent_synthesis_tabfact(title: str, question: str, headers: list, total_rows: int, outputs: list):
    return f"""You are AGENT_SYN a Synthesis expert for tables (2D), responsible for analyzing ,synthesising and verifying the claims using informations about each subtable . 
     Your task is to COMBINE  explanation of the claims of each subtable and  information from AGENTS to verify whether the provided claims are true or false on the FULL TABLE, the full table is a group of subtables.

     INSTRUCTIONS:
    1. Analyse your inputs :
     -Title: {title}
     -HEADERS: {headers}
     -CLAIM: {question}
     -TOTAL ROWS IN FULL TABLE: {total_rows}
    2. analyse AGENTS outputs (list format [AGENT_COL_0:output,AGENT_COL_2:output2,..ect] ):
      - outputs={outputs}
      - iterate over agents and analyse their explanations and there informations.
    3. collect all information and explanations provided by AGENTS.
    4. Review the claim 
    5. Generate the FINAL ANSWER  by combining AGENTS's outputs with your analysis (without extra information):
      -creticate your raisoning untill being sure about your final explanation about the full table
      -output the final explanation and verification to the claim answer is : (TRUE or FALSE )
    6.FORMAT output:
     - output the final answer between @@...@@ (e.g @@TRUE@@ or @@FALSE@@)
    """
