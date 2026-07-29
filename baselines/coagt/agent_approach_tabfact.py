
import re
import json

from utils.agents_prompt_tabfact import *

from utils.spliter_chunk import *
from tqdm import tqdm
path ='dataset_tabfact/data01.jsonl'
output_file = r"outputs\result_tabfact_data01.jsonl"

correct = 0
wrong = 0
t_samples = 0
empty_error_ids = []

with open(path, encoding='utf-8') as f1, open(output_file, "w", encoding="utf-8") as fw:


    for i, l in tqdm(enumerate(f1)):
        # time.sleep(2)


        # print('sample number -- ', i, "  : ", l)
        dic = json.loads(l) # convert json to dic

        ids = dic['table_id']
        title = dic['table_caption']
        headers = dic['table_text'][0]
        table = dic['table_text'][1:]
        total_rows=len( dic['table_text'][1:])
        # print('total_rows == ', total_rows)

        statement = dic['statement']
        # print('question == ', statement)
        label = dic['label']






        # Chunk the table
        chunks = chunk_table(table, max_tokens=1000)

        agents_outputs = ['']
        # chunks = [table[x:x + 100] for x in range(0, len(table), 100)]
        print("------------- Chain_of_Agent -------------\n")
        print(f"--- {len(chunks)} Agent_collector will proceed the table ---")
        row_pointer=1
        for i, subtable in enumerate(chunks):
            print(f"\n--- Subtable {i + 1} ({len(subtable)} rows) ---")
            row_rank=list(range(row_pointer,row_pointer+len(subtable)))
            print('row_rank == ',row_rank)
            k = prompt_agent_follow_tabfact(title,statement, headers, total_rows, agents_outputs[i], subtable, i+1,row_rank)
            k1 = get_completion(k,temperature=0.5, n=1)
            agents_outputs.append(f"AGENT_COL_{i+1}: {k1}")
            row_pointer=row_pointer+len(subtable)
            print(f"AGENT_COL_{i+1} \n: {k1}")

        ###### Agent synthesis ##########
        print("\n --- agent_synthesis ---")
        # print(agents_outputs)
        print("\n --- Collecte outputs, analyse, synthesis ---")
        result=prompt_agent_synthesis_tabfact(title,statement, headers, total_rows, agents_outputs)
        response = get_completion(result,temperature=0.7,n=1)
        print(' agent_synthesis output  ====')
        print(response)


        response=response.lower()
        output_ans = re.findall(r"@@(.*?)@@", response)[0]
        print(" ---- the prediction is : ",output_ans)

        if 'true' in output_ans:
            predict = 1
        elif 'false' in output_ans:
            predict = 0
        else:
            predict = 2

        if predict == label:
            correct += 1
        else:
            wrong += 1

        t_samples += 1

        print( '\nPrediction: ', predict, 'Gold: ', label)

        print('Correcet: ', correct, 'wrong: ', wrong, 'total: ', t_samples, "Accuracy: ",
              correct / (t_samples + 0.0001))

        # ---------------------------------------------------------------------------------------------------------
        tmp = {'key': ids, 'statement': statement, 'response': response,"prediction":predict, 'label': label}
        fw.write(json.dumps(tmp, ensure_ascii=False) + "\n")
        #

    fw.close()
    print('Final --> Correcet: ', correct, 'wrong: ', wrong, 'total: ', t_samples, "Accuracy: ",
          correct / (t_samples + 0.0001))
    print('empty_error_ids: ', empty_error_ids)



