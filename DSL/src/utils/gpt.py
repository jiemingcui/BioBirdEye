import os

from openai import OpenAI

if os.environ["OPENAI_API_KEY"] is None:
    raise Exception(
        "Please set the OPENAI_API_KEY using `export OPENAI_API_KEY=YOUR_API_KEY`."
    )

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
)

def request_openai(request):
    response = None
    i = 10
    while i > 0:
        try:
            response = client.chat.completions.create(
                model=request["model"],
                messages=request["messages"],
                max_tokens=request["max_tokens"],
                temperature=request["temperature"],
                top_p=request["top_p"],
            )
            break
        except Exception as e:
            print(e)
            i -= 1
    if response is None:
        return None
    return response.choices[0].message.content
