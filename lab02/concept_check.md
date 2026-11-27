# Lab 2: Architectures: A ReAct Agent From Scratch: Concept Check

## Q1. Classify a thermostat, a chess engine and a ReAct agent as reactive, deliberative or hybrid, with one reason each.
- **Thermostat:** **Reactive** — it maps the current temperature percept directly to a heating or cooling action using condition-action rules without planning ahead or storing a multi-step world model.
- **Chess engine:** **Deliberative** — it searches future board states and evaluates candidate move plans before choosing an action.
- **ReAct agent:** **Hybrid** — its `Thought` steps deliberate over subgoals and plans across steps, while each `Action` and `Observation` step reacts to the latest tool result or error from the environment.

## Q2. In the trace above, which lines are percepts, and which are actions?
- **Percepts:** The `Observation:` lines returned to the agent (`Observation: 1025` and `Observation: 175`), alongside the user's initial question.
- **Actions:** The `Action:` lines (with their `Action Input:` values) selected by the agent, such as `Action: calculator` with `4*185 + 3*95`, `Action: calculator` with `1200 - 1025`, and `Action: finish` with the final answer.

## Q3. Why do we pass `stop=["Observation:"]` when calling the model?
Passing `stop=["Observation:"]` stops the model from generating `Observation:` text itself, preventing it from inventing fake tool outputs instead of waiting for our Python code to execute the tool and supply the real observation.

## Q4. Map the trace above to the BDI terms belief, desire and intention.
- **Beliefs:** What the agent currently holds true from the conversation history and observations—such as starting with GHS 1,200, spending GHS 1,025 on the rice and oil, and having GHS 175 left.
- **Desires:** The agent's overall goal—determining how much money remains from the GHS 1,200 budget after buying the rice and oil.
- **Intentions:** The specific subgoal or step the agent commits to next in its `Thought`—computing `4*185 + 3*95` first, then subtracting `1025` from `1200`, and then calling `finish` with the result.