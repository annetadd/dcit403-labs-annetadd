# Lab 3: Percepts and Actions as Tools: Function Calling and MCP — Concept Check

## 1. One advantage and one disadvantage of native function calling compared with the Lab 2 text protocol
- **Advantage:** Tool names and arguments are returned as structured JSON tool calls enforced by the model/API schema, avoiding brittle regex or plain-text parsing failures when the model calls a tool.
- **Disadvantage:** It depends on the provider's native function-calling support and adds schema tokens to requests, which can occasionally trigger provider-specific tool formatting errors or slightly higher token usage.

## 2. Difference between a tool and a resource in MCP (with a pharmacy example of each)
- **Tool:** An executable action or query function exposed by the MCP server that the model or client invokes with arguments—for example, `record_sale(item, strength, qty)` or `list_expiring(days)`.
- **Resource:** Read-only data or context exposed by the server for an application or agent to read—for example, a read-only pharmacy stock catalogue or expiry summary resource.

## 3. Why `record_sale` should check quantity in code even when the system prompt says "never oversell"
System prompts only guide the model and can be bypassed by ambiguity, reasoning mistakes, or prompt injection. Enforcing positive quantities and available stock checks inside `record_sale` in Python guarantees that invalid sales or oversells are blocked even if the model requests them.

## 4. Which messages in the worked example are percepts?
- **Message 3 (`tool`):** Returns the stock data (`[{"item":"Amoxicillin","strength":"500mg","quantity":"40",...}]`) from the tool back to the agent as a percept (and **Message 1 (`user`)** is the initial user input/percept).