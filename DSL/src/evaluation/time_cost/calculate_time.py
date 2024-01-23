import os
import json
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.gpt import request_openai

dir_list = [
    "active_learning",
]

with open("data/ISA/labeled_isa_ver12.19.json", "r") as f:
    isa = json.load(f)

isa_map = {}
op_list = []
for key in isa:
    isa_map[key] = key
    op_list.append(key)
    for instruction in isa[key]["synonym"]:
        op_list.append(instruction)
        isa_map[instruction] = key


def query(key, sentence):
    request = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": """\
You are a helpful assistant.
You will be given a sentence and a operation. Please determine the time operation takes in the sentence.
Your output should be in JSON form and the unit you can choose is: s, min, h, day, week, month, year.
""",
            },
            {
                "role": "user",
                "content": """\
Operation: MEASURE
Sentence: Measure anisotropy using a Safire (Tecan Group Ltd.) fluorescent plate reader.
""",
            },
            {
                "role": "assistant",
                "content": """\
{
    "value": 5,
    "unit": "s"
}
""",
            },
            {"role": "user", "content": f"Operation: {key}\nSentence: {sentence}"},
        ],
        "max_tokens": 100,
        "temperature": 0.0,
        "top_p": 0.99,
    }
    response = request_openai(request)
    try:
        response = json.loads(response)
        value = response["value"]
        unit = response["unit"]
        if unit == "s":
            return int(value)
        elif unit == "min":
            return int(value) * 60
        elif unit == "h":
            return int(value) * 60 * 60
        elif unit == "day":
            return int(value) * 60 * 60 * 24
        elif unit == "week":
            return int(value) * 60 * 60 * 24 * 7
        elif unit == "month":
            return int(value) * 60 * 60 * 24 * 30
        elif unit == "year":
            return int(value) * 60 * 60 * 24 * 365
        else:
            print("parse error")
            return "error"
    except:
        print(response)
        print("GPT error")
        return "error"


def parse_time(string):
    value = string.split(" ")[0]
    unit = string.split(" ")[1]
    if unit == "s" or unit == "sec" or unit == "second":
        return int(value)
    elif unit == "min" or unit == "minute" or unit == "minutes":
        return int(value) * 60
    elif unit == "h" or unit == "hour" or unit == "hours":
        return int(value) * 60 * 60
    elif unit == "day" or unit == "days":
        return int(value) * 60 * 60 * 24
    elif unit == "week" or unit == "weeks":
        return int(value) * 60 * 60 * 24 * 7
    elif unit == "month" or unit == "months":
        return int(value) * 60 * 60 * 24 * 30
    elif unit == "year" or unit == "years":
        return int(value) * 60 * 60 * 24 * 365
    else:
        print(string)
        print("parse error")
        raise Exception("parse error")


def caluclate_time(item):
    for op in item["result"]:
        key = list(op.keys())[0]
        print(key)
        if key not in isa_map:
            get = False
            for attribute in op[key]["slot"]:
                if "time" == list(attribute.keys())[0]:
                    try:
                        op["time"] = {
                            "value": parse_time(attribute["time"]),
                            "from": "protocol",
                        }
                        print(">>> The operation described a time.")
                        get = True
                        break
                    except:
                        pass

            if not get:
                print(f">>> There is no {key}, let's go GPT!")
                op["time"] = {"value": query(key, op["sentence"]), "from": "gpt"}
        else:
            equal_key = isa_map[key]
            if (isa[equal_key]["execution_time"]["type"]) == "N/A":
                get = False
                for attribute in op[key]["slot"]:
                    if "time" == list(attribute.keys())[0]:
                        try:
                            op["time"] = {
                                "value": parse_time(attribute["time"]),
                                "from": "protocol",
                            }
                            print(">>> The operation described a time.")
                            get = True
                            break
                        except:
                            pass
                if not get:
                    print(
                        f">>> There is {key} in ISA, but I can't see the time, let's go GPT!"
                    )
                    op["time"] = {"value": query(key, op["sentence"]), "from": "gpt"}
            elif (isa[equal_key]["execution_time"]["type"]) == "range":
                print(f">>> Used {key} in ISA.")

                time = 0
                if isa[equal_key]["execution_time"]["unit"] == "min":
                    average = (
                        isa[equal_key]["execution_time"]["min"]
                        + isa[equal_key]["execution_time"]["max"]
                    ) / 2
                    time = average * 60
                elif isa[equal_key]["execution_time"]["unit"] == "s":
                    average = (
                        isa[equal_key]["execution_time"]["min"]
                        + isa[equal_key]["execution_time"]["max"]
                    ) / 2
                    time = average
                else:
                    print("unit error")
                    time = "unit error"
                op["time"] = {"value": time, "from": "isa"}
            else:
                print("type error")
    return item


for dir in dir_list:
    dir_path = f"output/{dir}/instructions/"
    for file in os.listdir(dir_path):
        if file.endswith(".json"):
            print(f"Processing {file}")
            with open(os.path.join(dir_path, file), "r") as f:
                data = json.load(f)
            for item in data:
                item = caluclate_time(item)
            output_path = f"output/{dir}/instructions_time/"
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            with open(os.path.join(output_path, file), "w") as f:
                json.dump(data, f, indent=4)
