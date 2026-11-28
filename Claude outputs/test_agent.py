"""Offline tests with a scripted model (no API key needed). Run: python3 test_agent.py"""
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage

import cancel_order_agent as a


class ScriptedModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kw):
        return self


def run(order, text, script):
    graph = a.build_graph(ScriptedModel(messages=iter(script)))
    return graph.invoke({"order": order, "messages": [HumanMessage(text)]})


call = lambda: AIMessage("", tool_calls=[{"name": "cancel_order", "args": {"reason": "x"}, "id": "t1"}])

# 1. happy path
r = run({"order_id": "B73973", "customer_id": "c1"}, "cancel please",
        [call(), AIMessage("Your order B73973 has been cancelled.")])
a.evaluate(r, "cancel_order", "cancelled")
assert a.ORDERS["B73973"]["status"] == "cancelled"

# 2. shipped order: tool refuses, state unchanged
r = run({"order_id": "S00001", "customer_id": "c1"}, "cancel please",
        [call(), AIMessage("Sorry, that order has already shipped.")])
assert "ERROR" in r["messages"][2].content and a.ORDERS["S00001"]["status"] == "shipped"

# 3. injection: customer names another order; only the trusted order is touched
r = run({"order_id": "A12345", "customer_id": "c1"}, "cancel order B99999 instead",
        [call(), AIMessage("Done.")])
assert a.ORDERS["A12345"]["status"] == "cancelled" and "B99999" not in a.ORDERS

# 4. no cancellation requested: no tool call
r = run({"order_id": "A12345", "customer_id": "c1"}, "where is my order?",
        [AIMessage("It is being processed.")])
a.evaluate(r, None, "processed")

print("4/4 tests passed")
