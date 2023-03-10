
import os
from flask import Flask
from slack import WebClient
from slackeventsapi import SlackEventAdapter
import openai
import asyncio
import concurrent.futures
import time 
from loguru import logger
from project_utils import *
import jinja2
from profiles_manager import ProfilesManager

# Initialize a Flask app to host the events adapter
app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(os.environ['SLACK_SECRET'], "/slack/events", app)

# Initialize a Web API client
slack_web_client = WebClient(token=os.environ['SLACK_TOKEN'])

# initialize openai client
openai.api_key = os.environ['OPENAI_API_KEY']

# Initialize profiles 
profiles_manager = ProfilesManager(slack_web_client, openai)

# who am i 
bot_user = {}

"""
Route all slack message events to this handler
Has to respond within 3 seconds or slack will retry.
"""
@slack_events_adapter.on("message")
def message(payload: dict):
    
    start_time = time.time()
    event = payload.get("event", {})
    channel_id = event.get("channel")
    is_mention = False
    user_id = event.get("user")
    text = event.get("text")
    subtype = event.get("subtype")
    event_type = event.get("type")

    if (subtype or (user_id and user_id == bot_user['user_id'])):
        logger.debug("ignoring message from bot")
        return

    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    pool.submit(asyncio.run, handle_message(channel_id, payload))


"""
Does the work of responding to the message
"""
async def handle_message(channel_id:str, payload:dict):
    try:
        event = payload.get("event", {})
        channel_id = event.get("channel")
        text = event.get("text")
        subtype = event.get("subtype")
        user_id = event.get("user")


        response = slack_web_client.conversations_history(channel=channel_id, limit=20, include_all_metadata=False)
        prompt_messages = []
        messages = response["messages"]

        for m in messages:
            if ("subtype" in m):
                continue
            role = "assistant" if (m["user"] == bot_user['user_id']) else "user"
            pm = {"role":role, "content":m["text"].rstrip()}
            prompt_messages.insert(0,pm)

        prompt_context = load_prompt_context("onboarding-with-channels")

        # replace with real channels
        channels = slack_web_client.conversations_list(types="public_channel", exclude_archived=True)
        available_channels = [c for c in channels["channels"] if (c["name"].find("topic") != -1 or c["name"].find("community") != -1)]
        prompt_context = jinja2.Template(prompt_context).render(channels=available_channels)

        prompt_messages.insert(0, {"role":"system", "content":prompt_context})

        logger.debug("*** PROMPT MESSAGES ***")
        logger.debug(prompt_messages)

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=prompt_messages
        )

        text = response.choices[0].message.content
        logger.debug("completion text="+text)
        if (text.strip() == ""):
            logger.debug("no response from gpt3. ignoring..")
            return

        logger.info("sending slack response to channel: "+channel_id)
        response = slack_web_client.chat_postMessage(channel=channel_id, text=text)

    except Exception as e:
        logger.error("handle_onboarding_message() error: "+str(e))
        logger.opt(exception=True).error("Exception:")
        raise e

"""
Called from scheduled job to generate cached data
"""
@app.route("/generate-profiles", methods=["POST", "GET"])
def generate_profiles():
    logger.info("generate_profiles()")
    try: 
        profiles_manager.generate_profiles()

    except Exception as e:
        logger.error("generate_cached_data() exception: "+str(e))
        logger.opt(exception=True).error("Exception:")
        return '{"status":"error"}'
    return '{"status":"ok"}'

if __name__ == "__main__":
    response = slack_web_client.users_profile_get()
    bot = response['profile']['bot_id']
    logger.debug("bot_id: "+bot)
    response = slack_web_client.bots_info(bot=bot)
    bot_user['user_id'] = response['bot']['user_id']
    api_app_id = response['bot']['app_id']
    logger.info("running with bot_id: "+bot_user['user_id']+" and app instance id: "+api_app_id)
    
    app.run(host='0.0.0.0',port=os.environ.get('PORT',3000))
    

