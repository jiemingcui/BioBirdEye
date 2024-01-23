import os
import json
import matplotlib.pyplot as plt
from nltk.translate.bleu_score import sentence_bleu
import seaborn as sns
import numpy as np
import networkx as nx
import nltk

nltk.download("punkt")
from nltk.tokenize import sent_tokenize
from scipy.stats import ttest_rel


def bleu_score(prediction, reference):
    return sentence_bleu([reference], prediction, weights=(1, 0, 0, 0))


def cal_accuracy(data, ground_l, name):
    key_list = []
    for first_index, i in enumerate(data):
        for second_index, k in enumerate(i["result"]):
            if "sentence" in k:
                key = list(k.keys())[0]
                key_list.append(key)
    ground_truth_key_list = []
    for index, j in enumerate(ground_l):
        ground_truth_key_list.append(j["instruction"])

    cover = 0
    for key in ground_truth_key_list:
        if key in key_list:
            cover += 1
    return cover / len(ground_truth_key_list)


def add_stars(p_value):
    if p_value < 0.001:
        return "***"
    elif p_value < 0.01:
        return "**"
    elif p_value < 0.05:
        return "*"
    else:
        return ""


def plot_box(data, category, title, filename, target_method="DSL"):
    category_map = {
        "DSL": "DSL",
        "baseline_1": "Direct + KG",
        "baseline_2": "Direct",
        "baseline_3": "Non-expert DSL + KG",
        "baseline_4": "Non-expert DSL",
    }

    # Transform data
    transformed_data = {category_map[cat]: data[cat][category] for cat in data}

    # Perform t-test with DSL as the reference method
    p_values = {}
    for method, values in transformed_data.items():
        if method != target_method:
            _, p_value = ttest_rel(
                transformed_data[target_method], values, alternative="greater"
            )
            p_values[method] = p_value

    plt.figure(figsize=(10, 6))

    # Create a box plot
    sns.boxplot(data=list(transformed_data.values()), showfliers=True)

    with open(f"output/data/{category}.csv", "w") as f:
        f.write("method,accuracy\n")
        for method, values in transformed_data.items():
            for value in values:
                f.write(f"{method},{value}\n")

    # Add p-values and stars to the plot
    for i, (method, p_value) in enumerate(p_values.items()):
        stars = add_stars(p_value)
        plt.text(
            i,
            max([max(transformed_data[target_method]), max(transformed_data[method])])
            + 2,
            f"p-value {method}: {p_value:.4f} {stars}",
            horizontalalignment="center",
            verticalalignment="center",
        )
        print(f"p-value {method}: {p_value:.4f} {stars}")

    plt.title(title)
    plt.xticks(range(len(transformed_data)), transformed_data.keys())
    plt.savefig(filename)


def draw_graph(edges, path):
    G = nx.DiGraph()
    G.add_edges_from(edges)
    pos = nx.circular_layout(G)
    nx.draw(
        G,
        pos,
        with_labels=True,
        node_size=100,
        node_color="skyblue",
        font_size=10,
        font_color="black",
        font_weight="bold",
        edge_color="gray",
        linewidths=1,
        arrowsize=20,
    )
    plt.savefig(path)
    plt.clf()


def compare_tree(ground_truth, node_match, edges, file_path, file_name):
    prediction = []
    reference = []
    for e in edges:
        if (e["from"]["index"], e["from"]["second_index"]) not in node_match or (
            e["to"]["index"],
            e["to"]["second_index"],
        ) not in node_match:
            continue
        if (
            node_match[(e["from"]["index"], e["from"]["second_index"])]
            == node_match[(e["to"]["index"], e["to"]["second_index"])]
        ):
            continue
        prediction.append(
            {
                "source": node_match[(e["from"]["index"], e["from"]["second_index"])],
                "target": node_match[(e["to"]["index"], e["to"]["second_index"])],
            }
        )

    for item in ground_truth["edges"]:
        reference.append(
            {"source": item["source"]["node_id"], "target": item["target"]["node_id"]}
        )

    cnt = 0
    for i in reference:
        if i in prediction:
            cnt += 1

    return cnt / len(reference)


def match_node(data, ground_l):
    node_match = {}
    wide_node_match = {}
    match_j = {}
    for first_index, i in enumerate(data):
        for second_index, k in enumerate(i["result"]):
            if "sentence" in i:
                find_match = False
                for index, j in enumerate(ground_l):
                    k["sentence"] = k["sentence"].split("notice:")[0].strip()
                    if index in match_j:
                        continue
                    ref_list = sent_tokenize(j["text"])
                    for ref in ref_list:
                        x = k["sentence"].replace("\\", "").strip().lower()
                        y = ref.replace("\\", "").strip().lower()
                        if x in y or y in x or bleu_score(x.split(), y.split()) > 0.6:
                            node_match[(first_index, second_index)] = j["id"]
                            wide_node_match[first_index] = j["id"]
                            find_match = True
                            match_j[index] = True
                            break
                    if find_match:
                        break
                if not find_match:
                    for index, j in enumerate(ground_l):
                        ref_list = sent_tokenize(j["text"])
                        for ref in ref_list:
                            x = k["sentence"].replace("\\", "").strip().lower()
                            y = ref.replace("\\", "").strip().lower()
                            if (
                                x in y
                                or y in x
                                or bleu_score(x.split(), y.split()) > 0.6
                            ):
                                node_match[(first_index, second_index)] = j["id"]
                                wide_node_match[first_index] = j["id"]
                                find_match = True
                                match_j[index] = True
                                break
                        if find_match:
                            break

                if not find_match:
                    if first_index in wide_node_match:
                        node_match[(first_index, second_index)] = wide_node_match[
                            first_index
                        ]

    return node_match


def cal(file_path):
    files = []
    print(file_path)
    for root, ds, fs in os.walk(f"output/{file_path}/instructions"):
        files.extend(fs)

    acc = []
    tree_acc_list = []

    for item in files:
        # if exist in ground truth
        name = item.split(".")[0]
        # print(name)
        if os.path.exists(f"data/full_ground_truth/{name}_graphData.json"):
            with open(f"data/full_ground_truth/{name}_graphData.json", "r") as f:
                ground_truth = json.load(f)
                if ground_truth["nodes"] == []:
                    continue
        else:
            continue

        if os.path.exists(f"output/ground_truth/{name}_graphData.json"):
            with open(f"output/ground_truth/{name}_graphData.json", "r") as f:
                ground_truth_edge = json.load(f)
                if ground_truth_edge["edges"] == []:
                    continue
        else:
            continue

        with open(f"output/{file_path}/instructions/" + item, "r") as f:
            data = json.load(f)
            if data == []:
                continue
        if os.path.exists(f"output/{file_path}/edges/" + item):
            with open(f"output/{file_path}/edges/" + item, "r") as f:
                edges = json.load(f)
        else:
            continue

        ground_l = []
        for i in ground_truth["nodes"]:
            ground_l.append(
                {"text": i["text"], "id": i["id"], "instruction": i["instruction"]}
            )

        ground_l_edge = []
        for i in ground_truth_edge["nodes"]:
            ground_l_edge.append(
                {"text": i["text"], "id": i["id"], "instruction": i["instruction"]}
            )
        accuracy = cal_accuracy(data, ground_l, name)
        acc.append(accuracy)

        node_match = match_node(data, ground_l_edge)

        tree_acc = compare_tree(ground_truth_edge, node_match, edges, file_path, name)
        tree_acc_list.append(tree_acc)

    return acc, tree_acc_list


def main():
    result = {
        "DSL": {},
        "baseline_1": {},
        "baseline_2": {},
        "baseline_3": {},
        "baseline_4": {},
    }

    for case in result:
        node, edge = cal(case)
        result[case]["node"] = node
        result[case]["edge"] = edge

    plot_box(result, "node", "Node Accuracy", "output/figure/node_accuracy.png")
    plot_box(result, "edge", "Edge Accuracy", "output/figure/edge_accuracy.png")


main()
