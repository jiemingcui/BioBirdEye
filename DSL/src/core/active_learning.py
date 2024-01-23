import json
import argparse
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.gpt import request_openai


def get_op_list(protocol, op_string, model):
    logging.info(">>> [get_op]" + protocol)
    if op_string is None:
        question = {"role": "user", "content": f"Protocol:\n{protocol}"}
    else:
        question = {
            "role": "user",
            "content": f"Protocol:\n{protocol}\nList:{json.dumps(op_string)}",
        }

    request = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": f"""\
You are a helpful assistant. 

Task:
Given a protocol and a list of instructions, determine which part of the protocol is meaning a instruction.

Work Steps:
1. Read the protocol carefully.
2. Analyse the main steps of the protocol.
3. From the instruction list, select appropriate instructions that align with the protocol.
4. Output a JSON list of the selected instructions and the seperated protocols. 

Notes:
1. Some sentences are notices for the previous sentences. Please use as fewer instructions as possible to describe the protocol.
2. Output the instructions in right order that people can follow it to do the experiment.
(e.g. You need to calculate the concentration of the solution before you can use it.)
3. Make sure the words you choose are all in the list. If there is no exact match, please choose the most similar one. Do not ask for more information.
                """,
            },
            {
                "role": "user",
                "content": f"""
Protocol:
Take 2 ml of the solution into a 3 ml syringe and put a 27-gauge needle to the syringe. Avoid any air bubbles in the syringe.
""",
            },
            {
                "role": "assistant",
                "content": """
[
    {
        "instruction":"TAKE",
        "sentence":"Take 2 ml of the solution into a 3 ml syringe",
        "notice":"Avoid any air bubbles in the syringe."
    },
    {
        "instruction":"PUT",
        "sentence":"put a 27-gauge needle to the syringe.",
        "notice":"Avoid any air bubbles in the syringe."
    }
]
                """,
            },
            {
                "role": "user",
                "content": f"""
Protocol:
As soon as the perfusion is started, immediately cut the hepatic vein to allow perfusate to run as a waste.
                """,
            },
            {
                "role": "assistant",
                "content": """
[
    {
        "instruction":"CUT",
        "sentence": "As soon as the perfusion is started, immediately cut the hepatic vein to allow perfusate to run as a waste."
    }
]
                """,
            },
            question,
        ],
        "max_tokens": 1000,
        "temperature": 0,
        "top_p": 1,
    }
    ans = utils.request_openai(request)
    ans = ans.replace("\\", "\\\\")
    logging.info(ans)
    print(question)
    print(ans)
    try:
        return json.loads(ans)
    except:
        return []


def get_instruction(
    model, protocol, passage, manual, blank_file, example, full_sentence
):
    input_passage = []
    for item in passage:
        input_passage.append(
            {
                "instruction": item["instruction"],
                "emit_name": item["emit_name"],
                "protocol": item["protocol"],
            }
        )

    message = [
        {
            "role": "system",
            "content": """\
You are a helpful assistant.
Task:
You will receive a protocol and an associated manual in JSON format. 
Based on the instructions, fill in the blanks in the JSON manual using information from the protocol and its context.

Manual explanation:
- require: Indicates if the slot is required (1) or optional (0).
- type: Specifies the type of information needed, such as reagent, string, number, volume, time, device, etc.
- comment: Describes the slot.

Filling blanks step:
1. Read the protocol and the manual carefully.
2. Use the most fitting term from the protocol or its context to fill the blanks in the manual.
3. Required slots and emits (require = 1) must be filled. Only optional slots can not be filled.

Note:
1. The required slots and emits must be filled, if you can not find them in protocol and context, use your own knowledge to fill it.
2. Retain the prefix in the chosen term. For instance, use "1ml solution" instead of just "solution".
3. Consider the context first when filling the blanks, note the name may be different from the context.\
4. Make sure to specify the output.
5. Only output a single object.
""",
        },
        {
            "role": "user",
            "content": """\
Protocol:
Wash twice.

Context:
[{"name": "washed cells_0", "description" : "{1)  Wash cells in PBS supplemented with 2% FCS and incubate with mAb on ice for 30 min.}"}]

Manual: 
{"RINSE":{"slot":{"reagent1":{"require":1,"type":"string","comment":"The object to be rinsed"},"reagent2":{"require":1,"type":"reagent","comment":"The material used to rinse the object,defult = water"},"repeat":{"require":0,"type":"number","comment":"Number of times the object should be rinsed, default=1"},"time":{"require":0,"type":"time","comment":""},"notice":{"require":0,"type":"string","comment":""}},"emit":{"reagent0":{"require":1,"type":"reagent","comment":"The object after rinsing"}}}}

Example sentence:
[Rinse]{operation} the [wafer]{reagent1} in [DI water]{reagent2} for [10 seconds]{time}.

File need to be filled:
{"reagent1":"<blank>","reagent2":"<blank>","repeat":"<blank>","time":"<blank>","notice":"<blank>","output":"<blank>"}
""",
        },
        {
            "role": "assistant",
            "content": """\
{"reagent1":"washed cells_0","reagent2":"PBS","repeat":"2","output":"washed cells_0"}
""",
        },
        {
            "role": "user",
            "content": f"""\
Protocol:
{protocol}

Full sentence:
{full_sentence}

Context:
{input_passage}

Manual: 
{manual}

Example sentence:
{example}

File need to be filled:
{blank_file}
                """,
        },
    ]

    print(message)

    request = {
        "model": model,
        "messages": message,
        "max_tokens": 1000,
        "temperature": 0,
        "top_p": 1,
    }

    resp = utils.request_openai(request)
    resp = resp.replace("\\", "\\\\")
    print(f">>> [get_instruction] GPT_response: {resp} ")
    resp = json.loads(resp)
    del_list = []
    for item in resp:
        if resp[item] == "None":
            del_list.append(item)
    for x in del_list:
        del resp[x]
    manual = json.loads(manual)
    key = list(manual.keys())[0]
    out = {key: {"emit": [], "slot": []}}

    for item in resp:
        if item in manual[key]["slot"]:
            out[key]["slot"].append({item: resp[item]})
        elif item in manual[key]["emit"]:
            out[key]["emit"].append({item: resp[item]})
        elif item == "output":
            out[key]["emit"].append({"reagent0": resp[item]})
        else:
            raise Exception("Unknown type")

    logging.info(out)
    return out


def link_edges(passage, instruction, index, second_index):
    print(">>> [link_edges] passage " + str(passage))
    print(">>> [link_edges] instruction " + str(instruction))

    edges = []
    key = list(instruction.keys())[0]
    used = []
    for item in instruction[key]["slot"]:
        name = list(item.keys())[0]
        for i in range(len(passage)):
            if passage[i]["emit_name"] == item[name]:
                edges.append(
                    {
                        "from": {
                            "index": passage[i]["index"],
                            "second_index": passage[i]["second_index"],
                        },
                        "to": {"index": index, "second_index": second_index},
                    }
                )
                used.append(i)
                break

    new_passage = []
    for item in passage:
        if passage.index(item) not in used:
            new_passage.append(item)
    return edges, new_passage


def get_instruction_without_manual(model, protocol, passage, op):
    input_passage = []
    for item in passage:
        input_passage.append(
            {
                "instruction": item["instruction"],
                "emit_name": item["emit_name"],
                "protocol": item["protocol"],
            }
        )

    message = [
        {
            "role": "system",
            "content": """\
You are a helpful assistant.
Task:
You will receive a protocol and its context.
Please use a JSON format to describe the protocol.

Filling blanks step:
1. Read the protocol carefully.
2. choose items and conditions from the protocol and its context to describe the protocol.

Note:
1. Since the protocol is a workflow, in most cases, the input of the next step is the output of the previous step.
2. You must specify the output, and only one output is allowed.
""",
        },
        {
            "role": "user",
            "content": """\
Protocol:
Wash twice.

Context:
[{"name": "washed cells_0", "description" : "{1)  Wash cells in PBS supplemented with 2% FCS and incubate with mAb on ice for 30 min.}"}]

Word:
RINSE
""",
        },
        {
            "role": "assistant",
            "content": """\
{"RINSE":{"reagent1":"washed cells_0","reagent2":"PBS","repeat":"2","output":"washed cells_0"}}
""",
        },
        {
            "role": "user",
            "content": f"""\
Protocol:
{protocol}

Context:
{input_passage}

Word:
{op}
                """,
        },
    ]

    request = {
        "model": model,
        "messages": message,
        "max_tokens": 1000,
        "temperature": 0,
        "top_p": 1,
    }

    resp = utils.request_openai(request)
    resp = resp.replace("\\", "\\\\")
    print(f">>> [get_instruction_without_manual] GPT_response: {resp} ")
    resp = json.loads(resp)
    del_list = []
    for item in resp[op]:
        if resp[op][item] == "None":
            del_list.append(item)
    for x in del_list:
        del resp[op][x]

    reform = {}
    if "output" in resp[op]:
        reform["emit"] = [{"reagent0": resp[op]["output"]}]
    else:
        reform["emit"] = []
    reform["slot"] = []
    for item in resp[op]:
        if item != "output":
            reform["slot"].append({item: resp[op][item]})
    resp[op] = reform

    logging.info(resp)
    return resp


def extract_emit(instruction):
    out = []
    key = list(instruction.keys())[0]
    for item in instruction[key]["emit"]:
        out.append(item)
    return out


def get_knowledge_graph(model, sentence):
    message = [
        {
            "role": "system",
            "content": """
You are a helpful assistant.
Task:
You will receive a sentence. Please do information extraction.
""",
        },
        {
            "role": "user",
            "content": f"""
Collect minced tissue with 2 ml DMEM and filter cells through 70 μm cell strainer.
""",
        },
        {
            "role": "assistant",
            "content": """
[Collect]{operation} [minced tissue]{reagent} with [2 ml DMEM]{reagent} and [filter]{operation} [cells]{reagent} through [70 μm cell strainer]{equipment}.
""",
        },
        {
            "role": "user",
            "content": f"""
{sentence}
""",
        },
    ]

    request = {
        "model": model,
        "messages": message,
        "max_tokens": 1000,
        "temperature": 0,
        "top_p": 1,
    }

    resp = utils.request_openai(request)
    resp = resp.replace("\\", "\\\\")
    print(f">>> [get_knowledge_graph] GPT_response: {resp} ")
    return resp


def compile_text(
    op_list, isa, protocol, isa_map, passage, model, index, Knowledge_Graph
):
    logging.info(f">>> [compile_text] protocol: {protocol}")
    logging.info(f">>> [compile_text] passage: {passage}")

    op_list = get_op_list(protocol, op_list, model)
    out = []
    edges = []

    for second_index, item in enumerate(op_list):
        op = item["instruction"]
        sentence = item["sentence"]
        if "notice" in item:
            sentence += "\nnotice:\n" + item["notice"]

        if isa is None:
            manual = None
            blank_file = None
            example = None
        else:
            try:
                map_op = isa_map[op]
                manual = {op: isa[map_op]}
                if "example" in manual[op]:
                    del manual[op]["example"]
                if "notice" in manual[op]:
                    del manual[op]["notice"]
                if "synonym" in manual[op]:
                    del manual[op]["synonym"]

                if "emit" in manual[op] and len(manual[op]["emit"]) > 0:
                    key = list(manual[op]["emit"].keys())[0]
                    manual[op]["emit"] = {
                        "output": {
                            "require": 1,
                            "type": manual[op]["emit"][key]["type"],
                            "comment": "The output",
                        }
                    }
                manual = json.dumps(manual)
                logging.info(f">>> [compile_text] manual: {manual}")

                blank_file = {}

                for slot in isa[map_op]["slot"]:
                    blank_file[slot] = "<blank>"
                for emit in isa[map_op]["emit"]:
                    blank_file[emit] = "<blank>"
                blank_file = json.dumps(blank_file)
                logging.info(f">>> [compile_text] blank_file: {blank_file}")
                with open("data/compilation/few_shot_examples.json", "r") as f:
                    examples = json.load(f)
                example = examples[map_op]
            except KeyError:
                manual = None
                blank_file = None
                example = None

        if Knowledge_Graph:
            new_sentence = get_knowledge_graph(model, sentence)
            if manual is None:
                instruction = get_instruction_without_manual(
                    model, new_sentence, passage, op
                )
                instruction[
                    "warning"
                ] = f"{op} not in ISA, using own knowledge to generate instruction."
            else:
                instruction = get_instruction(
                    model, new_sentence, passage, manual, blank_file, example, protocol
                )
            instruction["knowledge_graph"] = new_sentence
        else:
            if manual is None:
                instruction = get_instruction_without_manual(
                    model, sentence, passage, op
                )
                instruction[
                    "warning"
                ] = f"{op} not in ISA, using own knowledge to generate instruction."
            else:
                instruction = get_instruction(
                    model, sentence, passage, manual, blank_file, example, protocol
                )
        instruction["sentence"] = sentence

        out.append(instruction)

        edges_i, passage = link_edges(passage, instruction, index, second_index)
        edges.extend(edges_i)

        for i in extract_emit(instruction):
            reagent_name = list(i.keys())[0]
            passage.append(
                {
                    "instruction": op,
                    "emit_name": i[reagent_name],
                    "protocol": sentence,
                    "index": index,
                    "second_index": second_index,
                }
            )

    return out, edges, passage


def compile_list(op_list, isa, protocol, isa_map, model, Knowledge_Graph):
    passage = []
    out = []
    edges = []
    index = 0
    for item in protocol:
        if (
            item["type"] == "title"
            or item["content"].strip() == ""
            or len(item["content"]) < 5
        ):
            continue
        elif item["type"] == "string":
            out_i, edges_i, passage = compile_text(
                op_list,
                isa,
                item["content"],
                isa_map,
                passage,
                model,
                index,
                Knowledge_Graph,
            )
            out.append({"sentence": item["content"], "result": out_i})
            edges.extend(edges_i)
            index += 1
    return out, edges, passage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="gpt-4")
    parser.add_argument("--file", type=str, default="")
    args = parser.parse_args()
    model = args.model
    file = args.file
    compile_type = "active_learning"
    with open("data/compilation/labeled_isa_ver12.19.json", "r") as f:
        isa = json.load(f)

    os.makedirs(f"output/{compile_type}/instructions/", exist_ok=True)
    os.makedirs(f"output/{compile_type}/edges/", exist_ok=True)

    Knowledge_Graph = False

    if isa is None:
        isa_map = None
        op_list = None
    else:
        isa_map = {}
        op_list = []
        for key in isa:
            isa_map[key] = key
            op_list.append(key)
            for instruction in isa[key]["synonym"]:
                op_list.append(instruction)
                isa_map[instruction] = key

    with open(file.replace(".json", "_graphData.json"), "r") as f:
        data = json.load(f)

    f_name = file.split("/")[-1]
    print(f">>> [main] f_name: {f_name}")
    try:
        with open(f"output/{compile_type}/instructions/" + f_name, "r") as f:
            out = json.load(f)
    except FileNotFoundError:
        out = []
    if out:
        print(f"output/{compile_type}/instructions/" + f_name)
        print(">>> [main] " + str(len(out)) + " instructions already generated.")
        return

    new_data = []
    for item in data["nodes"]:
        new_data.append({"type": "string", "content": item["text"]})

    compiled_list, edges, _ = compile_list(
        op_list, isa, new_data, isa_map, model, Knowledge_Graph
    )

    with open(f"output/{compile_type}/instructions/" + f_name, "w") as f:
        json.dump(out + compiled_list, f, indent=4, ensure_ascii=False)
    with open(f"output/{compile_type}/edges/" + f_name, "w") as f:
        json.dump(edges, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
