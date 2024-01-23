import os
import json
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter


def calculate_time(data, str):
    t = 0
    for i in data:
        if i["sentence"] == str:
            for j in i["result"]:
                if j["time"]["value"] == "error":
                    continue
                t += j["time"]["value"]
            break
    return t


def combine_cycles(G):
    try:
        # Find a cycle
        cycle = nx.find_cycle(G, orientation="original")

        # Calculate the sum of weights in the cycle
        cycle_weight = 0
        for node_from, _, _ in cycle:
            cycle_weight += G.nodes[node_from]["time_cost"]
            print(f"node: {node_from}")
            print(f"node_weight: {G.nodes[node_from]['time_cost']}")

        print(f"cycle: {cycle}")
        print(f"cycle_weight: {cycle_weight}")

        # Create a new node with the combined weight
        new_node = max(G.nodes) + 1
        G.add_node(
            new_node,
            label=", ".join([G.nodes[node]["label"] for node, _, _ in cycle]),
            time_cost=cycle_weight,
        )
        print(f"added: {new_node}({cycle_weight})")

        # Redirect edges to the new node and remove old nodes
        for node, _, _ in cycle:
            # Redirect incoming edges
            for pred in list(G.predecessors(node)):
                if pred not in [n for n, _, _ in cycle]:
                    if not G.has_edge(pred, new_node):
                        G.add_edge(pred, new_node)
                        print(f"added: {pred} -> {new_node}")

            # Redirect outgoing edges
            for succ in list(G.successors(node)):
                if succ not in [n for _, n, _ in cycle]:
                    if not G.has_edge(new_node, succ):
                        G.add_edge(new_node, succ)
                        print(f"added: {new_node} -> {succ}")

            # Remove the old node
            G.remove_node(node)
            print(f"removed: {node}")

        # Call the function recursively in case there are more cycles
        combine_cycles(G)

    except nx.NetworkXNoCycle:
        # No more cycles, exit the function
        return


def create_gantt_chart_seconds(tasks, filename):
    # Determine the figure size dynamically based on the number of tasks
    fig_height = max(
        2, 0.5 * len(tasks)
    )  # 0.5 unit height per task, with a minimum of 2
    fig, ax = plt.subplots(
        figsize=(20, fig_height)
    )  # Width is fixed, height is dynamic

    # Create a Gantt chart in reverse order so the last task appears at the bottom
    for i, task in enumerate(reversed(tasks)):
        ax.barh(
            i,
            task["time_cost"],
            left=task["start_time"],
            color="skyblue",
            edgecolor="grey",
        )

    # Set the y-axis labels in reverse order
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels([task["name"] for task in reversed(tasks)])

    # Set the x-axis labels to show seconds
    ax.set_xlabel("Time (seconds)")
    plt.title(f"Gantt Chart of {filename}")
    plt.grid(axis="x")

    # Ensure directory exists
    os.makedirs("output/figure/gantt", exist_ok=True)

    # Save the figure
    plt.savefig(f"output/figure/gantt/{filename}.png")
    plt.close(fig)  # Close the figure to free up memory


def calculate_critical_path(data, reference, filename):
    G = nx.DiGraph()
    node_set = {}
    output_data = []
    for i, node in enumerate(reference["nodes"]):
        time_cost = calculate_time(data, node["text"])
        node_set[node["id"]] = i
        G.add_node(i, label=f"{i}({time_cost})", time_cost=time_cost)
        output_data.append({"operation": node["text"], "time_cost": time_cost})

    for edge in reference["edges"]:
        G.add_edge(
            node_set[edge["source"]["node_id"]], node_set[edge["target"]["node_id"]]
        )

    combine_cycles(G)

    connected_components = nx.weakly_connected_components(G)
    components_time_cost = []
    max_time_cost = 0
    for component in connected_components:
        component_cost = sum(G.nodes[node]["time_cost"] for node in component)
        start_time = 0
        for node in component:
            components_time_cost.append(
                {
                    "start_time": start_time,
                    "time_cost": G.nodes[node]["time_cost"],
                    "name": G.nodes[node]["label"],
                }
            )
            start_time += G.nodes[node]["time_cost"]
        path = " -> ".join(str(node) for node in component)

        if component_cost > max_time_cost:
            max_time_cost = component_cost
            critical_path = path

    create_gantt_chart_seconds(components_time_cost, filename)
    all_cost = sum(G.nodes[node]["time_cost"] for node in G.nodes)

    os.makedirs("output/data/operation_time", exist_ok=True)
    with open(f"output/data/operation_time/{filename}.json", "w") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)

    return critical_path, max_time_cost, all_cost


optimization_rate_map = {}

for filename in os.listdir("output/active_learning/instructions_time"):
    print(filename)
    filename = filename.split(".")[0]
    with open(f"output/active_learning/instructions_time/{filename}.json") as f:
        data = json.load(f)
    with open(f"data/ground_truth/{filename}_graphData.json") as f:
        reference = json.load(f)

    path, cost, all_cost = calculate_critical_path(data, reference, filename)
    optimization_rate_map[filename] = all_cost / cost

file_data = {}
dataframe = pd.read_excel(
    "data/protocol_type/annotated_protocols.xlsx", sheet_name="selected_protocols"
)
for index, row in dataframe.iterrows():
    protocol_ID = row["protocolId"]
    title = row["title"]
    topic = row["Topic"]
    file_data[protocol_ID] = {"title": title, "topic": topic}


output = []
for filename, rate in optimization_rate_map.items():
    output.append(
        {
            "filename": filename,
            "title": file_data[filename]["title"],
            "topic": file_data[filename]["topic"],
            "optimization_rate": rate,
        }
    )
with open("output/data/optimization_rate.json", "w") as f:
    json.dump(output, f, indent=4, ensure_ascii=False)

optimization_rate_map = dict(
    sorted(optimization_rate_map.items(), key=lambda item: item[1], reverse=True)
)

filenames = list(optimization_rate_map.keys())
optimization_rates = list(optimization_rate_map.values())
colors = ["green" if x >= 0 else "red" for x in optimization_rates]

# Plotting
fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(filenames, optimization_rates, color=colors)

# Adding line at y=0 for reference
ax.axhline(0, color="black", linewidth=0.8)

# Rotating x-axis labels if there are many filenames
ax.xaxis.set_tick_params(rotation=90)

# Setting y-axis label format to percentage
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: "{:.0%}".format(y)))

plt.title("Waterfall Graph of Optimization Rates")
plt.xlabel("Filename")
plt.ylabel("Optimization Rate")
plt.tight_layout()
plt.savefig("output/figure/waterfall.png")


# choose the top 10
optimization_rate_map = dict(
    sorted(optimization_rate_map.items(), key=lambda item: item[1], reverse=True)[:10]
)

for filename in optimization_rate_map.keys():
    print("top-10")
    print(filename)
    filename = filename.split(".")[0]
    with open(f"output/active_learning/instructions_time/{filename}.json", "r") as f:
        data = json.load(f)
    with open(f"data/ground_truth/{filename}_graphData.json", "r") as f:
        reference = json.load(f)
    os.makedirs("output/data/operation_time/top-10", exist_ok=True)
    os.makedirs("output/figure/gantt/top-10", exist_ok=True)
    path, cost, all_cost = calculate_critical_path(
        data, reference, f"top-10/{filename}"
    )
