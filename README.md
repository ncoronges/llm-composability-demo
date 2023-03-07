# LLM Composability App Demo 

The demo uses the Slack Events API and OpenAI's GPT-3.5 ChatCompletion API to simulate a community platform AI guide. The bot's primary mode is "onboarding", where it will interact with members, providing inights and recommendations and links to other channels.

To run locally grab source and activate environment.
```
git clone --branch master https://github.com/ncoronges/llm-composability-demo
cd llm-composability-demo
source ./env/bin/activate
pip install -r requirements.txt
```

To do local development you will need to set up the app to listen to events from the Slack API event dispatcher. That means your app has to be accessible on the internet (more on that below), and you will need an instance of slack configured to point to your local instance. 

To set up the app in slack, you'll need to create a new App and provide the necessary scopes: 
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

## Running on GCP server 

The bot uses Google Cloud Run for hosted instances. You will need to permission the GCP gcloud CLI app. This key for the dev server to be provided separately. 

```
export GOOGLE_APPLICATION_CREDENTIALS="/home/user/Downloads/my-key.json"
```

## Deployment to cloud run

The nice thing about Firestore is authentication is handled automatically in the Cloud Run environment. ATM we don't have CI/CD pipelines set up. Manual deployment looks like: 

```
gcloud config set project [YOUR PROJECT]
gcloud builds submit --tag gcr.io/[YOUR PROJECT]/gpt3-bloomberg-demo
gcloud run deploy --image gcr.io/[YOUR PROJECT]/gpt3-bloomberg-demo:latest --platform managed

```
You will need to set the keys in environment variables on cloud run

```
gcloud run services update gpt3-bloomberg-demo --update-env-vars SLACK_SECRET=<your slack secret>,SLACK_TOKEN=<slack token>,OPENAI_KEY=<open ai key>
```

Subsquently you can run the deplyment with

```
gcloud run deploy gpt3-bloomberg-demo --source .
```

Should be off to the races from here. 

## How the app works 

The app interacts with the world in two ways. It is triggered by an event from the Slack API, and it has a scheduled job that fires every 10 minutes. The scheduled job is mainly for caching data on user profiles and news items. 

The main operations of the app are managed in app.py where you will find the routing methods for events and the scheduled job API. 

```
@app.route("/scheduled-jobs/generate-cached-data", methods=["POST", "GET"])
def generate_cached_data():
```

and 

```
@slack_events_adapter.on("message")
def message(payload):
```

No other entries into the app exist. 

Most of the logic in the app leverages GPT3. There are otherways to handle some of the functionality but some license was taken in using GPT3 to explore its capabilties and limitations. For example, we generate user profiles from the chat messages in slack using text completion. A sequence of messages is used as a prompt and GPT-3 summarizes the messages in a simple descriptive string for the profile. 

Prompts are the main instructional code for GPT-3, for example, the profile summarization looks like this. 

prompts/profile.txt
```
Generate profiles about each user based on their chat history and use the description field in the JSON object to summarize their interests and current role.

CHAT:
<@U50101>: I'm a CTO at a large fitness brand based in Europe. Interested in all things sports, technology, and fitness tracking. When I can find the time, I'm out cycling and mountain climbing in the Alps.
<@U5B232>: I've been looking into investments in China and Asia more broadly. Primarily Investment banking. Also interested in Emerging tech, blockchain and crypto.
<@AI>: We'll make a note of that. Where are you based?
<@U5B232>: I'm based in Washington, DC, but I travel often to Hong Kong and London.

Profiles:
```json
{
    "U50101": 
    {
        "description":"CTO based in Europe whose professional interests include Sports, Technology and Finance. Personal interests include cylcing and mountain climbing."
    },
    "U5B232":
    {
        "description":"Interests include China and Asia, Investment Banking, Emerging tech, blockchain, and crypto. Based in Washington, D.C. but travels to London and Hong Kong"
    }
}
```

This is the few shot learning approach where a few examples are given to the API, and then the actual chat sequence, and the text completion API provides the profiles according to the schema defined above. 

Most of the operations of the app follow this pattern. 

There is some kludgy code to inject data into the prompts which is far from perfect. For example in the onboarding prompt we inject the actual resources and channels from slack into the prompt, here. 

```
AVAILABLE CHANNELS:{{
#community-tech: community for tech business leaders,
#topic-web3-crypto: topic channel focused on web3, crypto, nfts
#topic-AI: topic channel focused on AI, data and machine learning
#topic-fintech: topic focused on all things Fintech
}}

AVAILABLE RESOURCES:{{
"ChatGPT Dominates the Tech World":"overview of the megatrend around Generative AI"
"VC Roundup in Tech":"What you need to know about Venture trends and tech today"
"Climate Tech creating Whitespace Opportunities for Startups":"Overview of trends in Climate tech"
}}
```

The Jinja style templating language is used to insert data into the prompt at request time based on what resources and channels are available. For improvements to the process we may look at things like [ dust.tt](https://dust.tt)
