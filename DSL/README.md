## Domain Specfic Language

### Set Up Environment

```bash
conda create -n BioBirdEye python=3.11
conda activate BioBirdEye
pip install -r requirements.txt
```

### Usage

1. Preprocess the protocols

    ```bash
    python src/pre_process/separate.py
    ```

2. Set OpenAI API key

    ```bash
    export OPENAI_API_KEY=<your key here>
    ```

3. Compile the protocols

    Example usage:
    ```bash
    python src/core/compiler.py \
        --model gpt-3.5-turbo \
        --file data/parsed_protocols/protocol_nprot-4.json \
        --type DSL
    ```

4. Evaluate the comilation results

    **Correctness**
    ```bash
    python src/core/evaluation/correctness/calculate_critical_path.py
    ```

    **Time cost**
    ```bash
    python src/core/evaluation/time_cost/calculate_time.py
    ```
