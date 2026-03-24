## Python
- Create venv
- pip install -r requirements.txt


# From acyive venv  Run the server (auto-reload on file changes)
python -m uvicorn main:app --reload --port 8001


## .env
SECRET_KEY=cdfdf
JWT_EXPIRY_HOURS=24

DATABASE_PATH=nurser.db  ()

BULKSMS_USERNAME=cschlosser
BULKSMS_PASSWORD=NdGu5BjeXXj9hf.

agent_mail_nurser = am_us_813eaad4d64b880035ec9aca347b0625ffcb61d8ede276ca57d250068b9183f7

agentmail_inbox_id = nurser@agentmail.to

support_email = christian@ideaplant.co.uk

## Caddy file
