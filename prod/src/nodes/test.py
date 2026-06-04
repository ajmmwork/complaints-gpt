from openai import OpenAI

client = OpenAI()

instructions = """
You are a personal math tutor. When asked a math question,
write and run code using the python tool to answer the question.
"""

resp = client.responses.create(
    model="gpt-4.1",
    tools=[
        {
            "type": "code_interpreter",
            "container": {"type": "auto", "memory_limit": "4g"}
        }
    ],
    instructions=instructions,
    input="I need to solve the equation 3x + 11 = 14. Can you help me?",
)

print(resp.output)