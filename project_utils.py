from loguru import logger
import json
import re

def extract_json_from_text(text: str) -> dict:
      start_index = text.find('```json')
      end_index = text.find('```', start_index + 1)
      json_string = text[start_index + 7:end_index].strip()
      return json.loads(json_string)

def replace_channels_in_prompt(prompt: str, available_channels: list) -> str:
    variable = "CHANNELS"
    #sector_channels = {}
    channel_replace = ""
    for c in available_channels["channels"]:
        channel_replace += "#"+ c["name"] + ":" + c["purpose"]["value"]+"\n"
    
    prompt = re.sub(variable+":\{\{.*?\}\}", variable+":\n"+channel_replace, prompt, flags=re.S)
    return prompt

def load_prompt_context(prompt_context:str) -> str:
    context = None
    with open('prompts/'+prompt_context+'.txt') as f:
        context = f.read()
        logger.info("loaded prompt context for: "+prompt_context)

    return context