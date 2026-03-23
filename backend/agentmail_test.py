
import os
from dotenv import load_dotenv
load_dotenv()

from agentmail import AgentMail

base_url="https://api.agentmail.to/v0/inboxes/nurser@agentmail.to/messages/send"

client = AgentMail(    
    api_key=os.getenv("agent_mail_nurser"),
)

respose = client.inboxes.messages.send(
    inbox_id=os.getenv("agentmail_inbox_id"),
    to=os.getenv("support_email"),
    subject="Feedback de Nurser -test",
    text="TEXTO AQUI",
)


print(respose)