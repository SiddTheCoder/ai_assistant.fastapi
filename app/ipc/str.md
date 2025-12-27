app/
├── main.py
├── config.py

├── core/                     # CORE RUNTIME (heart of system)
│   ├── orchestrator.py        # registers tasks, schedules execution
│   ├── executor.py            # runs server-side tools
│   ├── execution_state.py     # ExecutionState, TaskRecord
│   ├── task_queue.py          # pending / runnable tasks
│   └── binding_resolver.py    # resolves input_bindings (later)

├── models/                   # PURE DATA MODELS
│   ├── task.py                # Task (plan-level)
│   ├── task_record.py
│   ├── execution_state.py
│   └── outputs.py

├── planner/                  # LLM-related (keep isolated)
│   ├── planner.py             # converts user query → Task[]
│   ├── prompts/
│   └── validators.py

├── tools/                    # SERVER TOOL IMPLEMENTATIONS
│   ├── base.py                # ToolAdapter base class
│   ├── web/
│   │   └── web_search.py
│   └── system/
│       └── system_info.py

├── registry/
│   ├── tool_registry.json
│   └── loader.py              # loads & validates registry

├── api/                      # FastAPI routes
│   ├── routes/
│   │   ├── run.py
│   │   └── status.py
│   └── websocket.py

├── ipc/                      # Server ↔ Client protocol
│   ├── messages.py
│   └── emitter.py

├── persistence/
│   ├── state_store.py         # save/load ExecutionState
│   └── history.py

├── utils/
│   └── jsonpath.py
