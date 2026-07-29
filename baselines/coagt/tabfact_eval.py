def main():

    import json

 
    filename ="outputs/tabfact_final_result.jsonl"


    print('Start', filename)
    correct = 0
    wrong = 0
    sample = 0

    with open(filename, 'r',encoding='utf-8') as f:
        for line in f:
            output = json.loads(line)
            if 'response' in output:
                # pred_answer = output['prediction']
                prediction = output['prediction']
                label = output['label']
                # print(pred_answer,target_values, type(pred_answer), type(target_values))

                # if 'not possible to verify' in response:
                #     predict = 2
                # if 'cannot be verified' in response:
                #     predict = 2
                # elif 'no information' in response:
                #     predict = 2
                # elif 'cannot be determined' in response:
                #     predict = 2
                if  prediction == 1:
                    predict = 1
                elif  prediction == 0:
                    predict = 0


                if predict == label:
                    correct += 1
                else:
                    wrong += 1
                    print('sample#:', sample, output['key'],'prediction', predict,'label',label)
                    # print(output)
            else:
                continue
            sample += 1

            if sample % 100 == 0:
                print('Accuracy', correct / (correct + wrong))
                print('Corect: ', correct, 'Wrong: ', wrong, "Total: ", (correct + wrong))

    print('Accuracy', correct / (correct + wrong))
    print('Corect: ', correct, 'Wrong: ', wrong, "Total: ", (correct+wrong))

if __name__ == '__main__':
    main()

