from loguru import logger
from project_utils import load_prompt_context, extract_json_from_text
import openai
import jinja2

EMBEDDINGS_MODEL = "text-embedding-ada-002"

class ProfilesManager:
    def __init__(self, slack_app, openai_app):
        self.slack_web_client = slack_app
        self.openai = openai_app
        self.profiles = None
    
    def generate_profiles(self):

        if (self.profiles is None):
            self.profiles = {}

        logger.info("Generating profiles ...")
        # creatiung profiles for users
        available_channels = self.slack_web_client.conversations_list(types="public_channel", exclude_archived=True)
        prompt_messages = []
        for c in available_channels["channels"]:
            if (c["name"].find("member-onboarding") != -1):
                response = self.slack_web_client.conversations_history(channel=c["id"], limit=50, include_all_metadata=False)
                logger.info("got conversation history for channel: "+c["name"])
                messages = response["messages"]
                # get only messages which have no subtype
                prompt_messages += [m for m in messages if "subtype" not in m]
        # sort by timestamp
        prompt_messages = sorted(prompt_messages, key=lambda d: d['ts'])[:50]

        if(len(prompt_messages) > 0):
            prompt_context = load_prompt_context("profiles")
            prompt = jinja2.Template(prompt_context).render(messages=prompt_messages)

            logger.debug("prompt=\n"+prompt)
            response = self.openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=512,
            )
            text = response.choices[0].text
            logger.debug("completion text="+text)
            json_data = extract_json_from_text(text)
            logger.debug("json_data="+str(json_data))
            for k, v in json_data.items(): 
                v["id"] = k
                self.profiles[k] = v
            logger.info("loaded {} profiles total".format(len(self.profiles)))

                
    def get_user_profile(self, user_id):
        if (user_id in self.profiles):
            return self.profiles[user_id]
        else:
            return None

    def get_all_profiles(self):
        if (self.profiles is None):
            self.generate_profiles()
        return self.profiles

    