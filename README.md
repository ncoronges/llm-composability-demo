# LLM Composability App Demo 

The demo uses the Slack Events API and OpenAI's GPT-3.5 ChatCompletion API to simulate a community platform AI guide. The bot's primary mode is "onboarding", where it will interact with members, providing inights and recommendations and links to other channels. 

This code accompanies post I did here: https://medium.com/@ncoronges/composability-in-llm-apps

To run locally grab source and activate environment.
```
git clone --branch master https://github.com/ncoronges/llm-composability-demo
cd llm-composability-demo
source ./env/bin/activate
pip install -r requirements.txt
```

To do local development you will need to set up the app to listen to events from the Slack API event dispatcher. That means your app has to be accessible on the internet (more on that below), and you will need an instance of slack configured to point to your local instance. 

To set up the app in slack, you'll need to create a new App and provide the necessary scopes. (You may be able to setup with the slack_app_manifest.yaml file included in repo but this is still a beta feature in slack.) 

- channels:history
- chat:write
- im:write
- pins:read
- reactions:read
- users.profile:read
- users:read
- chat:write
- channels:read
- groups:read
- mpim:read

Grab the client signing secret and oauth access token. 

Create keys for openai and slack instance
```
export SLACK_SECRET=your slack app secret ("Signing Secret")
export SLACK_TOKEN=your slack token (OAuth & Permissions > Add to Workspace > "Bot User OAuth Access Token")
export OPENAI_KEY=open ai (secret) key
```
You'll need to Enable events in the Slack app and set up a local server address, using something like [npx](https://github.com/localtunnel/localtunnel) or ngrok to create a reverse proxy for Slack callbacks.

```
python3 app.py
npx localtunnel --port 3000
```

A tip when running localtunnel is to fix the subdomain once you get one. Lt does crash when the underlying service changes unlike ngrok. 

```
npx localtunnel --subdomain <your subdomain> --port 3000
```

Once you grab your public URL from npx, go back to your Slack app (https://api.slack.com/apps).
Under 'Event Subscriptions', click on "Enable events" set 'https://<npx URL>/slack/events'. Subscribe to the following events:
```
- message.channels
- message.groups
- app_mention
```
