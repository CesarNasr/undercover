"""Isolated acceptance server with scripted model replies, never OpenRouter."""
import os
import tempfile
import time

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from agent.main import run
from backend import runs
from backend.main import app

_directory = tempfile.TemporaryDirectory()
os.environ['UNDERCOVER_DB'] = os.path.join(_directory.name, 'acceptance.sqlite3')

class ScriptedModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self

def scripted(claim_id, thread_id):
    time.sleep(1.5)
    outcome, amount = {'CLM-1001': ('approve', '420'), 'CLM-1002': ('approve', '1250'), 'CLM-1003': ('decline', '0'), 'CLM-1004': ('refer', '0')}[claim_id]
    calls = [('read_context', {}), ('record_decision', dict(outcome=outcome, payout=amount, calculation='Synthetic acceptance calculation', explanation='Synthetic evidence checked. Policy section 3 applies.', policy_references=['3']))]
    if outcome == 'approve':
        calls.append(('request_payment', {'amount': amount}))
    messages = [AIMessage(content='', tool_calls=[{'name': name, 'args': args, 'id': str(i)}]) for i, (name, args) in enumerate(calls)]
    messages.append(AIMessage(content='Complete'))
    return run(claim_id, thread_id, ScriptedModel(messages=iter(messages)))

runs.run = scripted
