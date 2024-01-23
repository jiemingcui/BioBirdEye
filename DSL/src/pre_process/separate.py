import json
import os
import re
from tqdm import tqdm
import html
from concurrent.futures import ThreadPoolExecutor


def html_decoder(html_text):
    return html.unescape(html_text)


def split_text(text: str, expression: str):
    matches = re.findall(expression, text)
    parts = re.split(expression, text)
    result = []
    if parts[0].strip() != "":
        result.append(parts[0])
    assert len(matches) == len(parts) - 1
    for i, part in enumerate(parts[1:]):
        body = html_decoder(part.strip())
        result.append({"title": matches[i].strip(), "body": body})
    if len(result) == 1 and isinstance(result[0], str):
        return result[0]
    return result


def split_dict(text: list, expression: str):
    out = []
    for item in text:
        if isinstance(item, str):
            slice_string = split_text(item, expression)
            if isinstance(slice_string, str):
                out.append(slice_string)
            elif isinstance(slice_string, list):
                for s in slice_string:
                    out.append(s)
        elif isinstance(item, dict):
            if isinstance(item["body"], str):
                item["body"] = split_text(item["body"], expression)
            elif isinstance(item["body"], list):
                item["body"] = split_dict(item["body"], expression)
            else:
                raise Exception("Unknown type")
            out.append(item)
        else:
            raise Exception("Unknown type")
    return out


def find_first_match_text(text: str, patterns: dict):
    # Initial values for earliest match
    earliest_pos = float("inf")
    earliest_pattern_name = None

    # Iterate over patterns to find the earliest match
    for pattern_name, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            if match.start() < earliest_pos:
                earliest_pos = match.start()
                earliest_pattern_name = pattern_name

    if earliest_pattern_name:
        return earliest_pattern_name
    else:
        return None


def find_first_match_dict(text: list, patterns: dict):
    for item in text:
        if isinstance(item, str):
            earliest_pattern_name = find_first_match_text(item, patterns)
            if earliest_pattern_name is not None:
                return earliest_pattern_name
        elif isinstance(item, dict):
            if isinstance(item["body"], str):
                earliest_pattern_name = find_first_match_text(item["body"], patterns)
                if earliest_pattern_name is not None:
                    return earliest_pattern_name
            elif isinstance(item["body"], list):
                earliest_pattern_name = find_first_match_dict(item["body"], patterns)
                if earliest_pattern_name is not None:
                    return earliest_pattern_name
            else:
                raise Exception("Unknown type")
        else:
            raise Exception("Unknown type")
    return None


def do_split(text, patterns):
    while True:
        if isinstance(text, str):
            earliest_pattern_name = find_first_match_text(text, patterns)
        elif isinstance(text, list):
            earliest_pattern_name = find_first_match_dict(text, patterns)
        else:
            raise Exception("Unknown type")
        if earliest_pattern_name is None:
            break
        if isinstance(text, str):
            text = split_text(text, patterns[earliest_pattern_name])
        elif isinstance(text, list):
            text = split_dict(text, patterns[earliest_pattern_name])
        else:
            raise Exception("Unknown type")
    return text


def split_into_sentences(text):
    patterns_1 = {
        "Bold": r"(?:^|[\n\r]+)\*\*.*?\*\*[\s+|.]",
        "Number followed by ).": r"(?:^|[\n\r]+|[ ]+[ ])\d{1,2}\)\.[ ]",
        "Number followed by )": r"(?:^|[\n\r]+|[ ]+[ ])\d{1,2}\)",
        "Number followed by .": r"(?:^|[\n\r]+|[ ]+[ ])\s*\d{1,2}\.(?:!\d|[ |\u00a0])",
        "Number followed by -": r"(?:^|[\n\r]+|[ ]+[ ])\d{1,2}-[ ]",
        "Number followed by space": r"(?:^|[\n\r]+|[ ]+[ ])\d+[ ](?=[A-Z][a-z])",
        "Number followed by |": r"(?:^|[\n\r]+|[ ]+[ ])\d{1,2}(?:\│|\||\∣)",
        "Lowercase letter followed by )": r"(?:^|[\n\r]+|[ ]+[ ])[a-z]\)[ ]",
        "Uppercase letter inside ()": r"(?:^|[\n\r]+|[ ]+[ ])\([A-Z]\)[ ]",
        "Step followed by a number": r"(?:^|[\n\r]+|[ ]+[ ])Step \d{1,2}.?[ ]",
        "roman number followed by ) or between ()": r"(?:^|[\n\r]+|[ ]+[ ])[\\\(]?[I|II|III|IV|V|VI|VII|VIII|IX|X|i|ii|iii|iv|v|vi|vii|viii|ix|x]\)",
        "A capital letter followed by :": r"(?:^|[\n\r]+|[ ]+[ ])[A-Z]\:[ ]",
    }

    text = do_split(text, patterns_1)

    patterns_2 = {
        "Number and letter followed by )": r"(?:^|\s+)\d{1,2}[a-z]\)[ ]",
    }

    text = do_split(text, patterns_2)
    return text


def parse_file(path, filename):
    with open(path + filename, "r") as f:
        data = json.load(f)
        procedure_text = ""
        for text in data["content"]:
            if text["header"] == "Procedure":
                procedure_text = text["content"]
        procedure_divided = split_into_sentences("\n" + procedure_text)
    return procedure_divided


def flatten_list(data: list):
    out = []
    for item in data:
        if isinstance(item, str):
            out.append({"type": "string", "content": item})
        elif isinstance(item, dict):
            out.append({"type": "title", "content": item["title"]})
            if isinstance(item["body"], str):
                if item["body"].strip() != "":
                    out.append({"type": "string", "content": item["body"]})
            elif isinstance(item["body"], list):
                out.extend(flatten_list(item["body"]))
            else:
                raise Exception("Unknown type")
        else:
            raise Exception("Unknown type")
    return out


def main():
    files = []
    for root, ds, fs in os.walk("data/protocols/"):
        files.extend(fs)
    for f_name in tqdm(files):
        protocols = parse_file("data/protocols/", f_name)
        protocols = flatten_list(protocols)
        os.makedirs("data/parsed_protocols/", exist_ok=True)
        with open("data/parsed_protocols/" + f_name, "w") as file:
            json.dump(protocols, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
