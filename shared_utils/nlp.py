import openai
import ast
from shared_utils.configurations import configurations
import re

openai.api_key = configurations.get('openai', 'api_key')


def generate_completion(prompt, max_tokens=50, temperature=0.8):
    """
    Generates completion(s) for a given prompt using GPT-3.

    :param prompt: The prompt to generate completion(s) for.
    :param max_tokens: The maximum number of tokens in the generated output.
    :param temperature: The creativity parameter (higher values result in more creative outputs).
    :return: A list of generated completions.
    """
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature
    )
    completions = [choice.text.strip() for choice in response.choices]
    return completions


def generate_chat_completion(messages, model="gpt-3.5-turbo", max_tokens=50, temperature=0.8):
    """
    Generates completion(s) for a given chat conversation using GPT-3 or GPT-4.

    :param messages: The list of message objects for the chat conversation.
    :param model: The model to use for the chat conversation.
    :param max_tokens: The maximum number of tokens in the generated output.
    :param temperature: The creativity parameter (higher values result in more creative outputs).
    :return: The assistant's reply as a string.
    """
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature
    )
    # Return the reply
    return response['choices'][0]['message']['content']


def generate_embedding(text):
    model_name = "text-embedding-ada-002"

    response = openai.Embedding.create(
        model=model_name,
        input=text
    )["data"][0]["embedding"]

    return response


def sanitize_ai_response(response_text):
    valid_structure = False
    while not valid_structure:
        if len(response_text) == 0:
            # TODO raise an appropriate exception
            break
        try:
            parsed_response = ast.literal_eval(response_text)
            valid_structure = True
        except (SyntaxError, ValueError):
            response_text = response_text[:-1]

    return parsed_response


def extract_json_string(text: str) -> str:
    json_pattern = r'{.*}'
    json_string = re.search(json_pattern, text, re.DOTALL)
    if json_string:
        return json_string.group()
    else:
        raise ValueError("No JSON string found in the input text")

