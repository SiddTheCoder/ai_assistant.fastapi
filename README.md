# AI Server & Orchestration System

A production-grade AI backend featuring **FastAPI**, **Socket.IO**, and a custom **Task Orchestration Engine**. This server handles voice/text interactions, manages user sessions, and executes complex multi-step tasks (File execution, Web browsing, System control) via a robust **Primary Query Handler (PQH)** -> **Server Query Handler (SQH)** architecture.

---

## 🏗️ Architecture Overview

The system is built on a **Dual-Layer Processing Architecture**:

1.  **PQH (Primary Query Handler)**: The "Face" of the AI.
    *   **Latency**: Ultra-low (<1s).
    *   **Responsibility**: Understands user intent, handles conversation, manages emotion, and **decides** if tooling is needed.
    *   **Response**: Returns an IMMEDIATE cognitive response to the client (`CognitiveState`), so the user is never waiting.
    
2.  **SQH (Semantic/Server Query Handler)**: The "Brain" of the AI.
    *   **Latency**: Variable (depends on task).
    *   **Responsibility**: Executes the heavy lifting. Runs in the background **PARALLEL** to the user reading/listening to the PQH response.
    *   **Component**: The `Orchestrator` manages task dependencies, parallel execution, and client-side delegation.

### The "Zero-Latency" Flow
1.  **User Query** -> **PQH**: "Find me a recipe for pancakes and save it to a file."
2.  **PQH Response** (Immediate): "Sure! I'm looking for a pancake recipe now and I'll save it for you." (Client starts TTS).
3.  **SQH Execution** (Background):
    *   *Step 1*: `web_search("pancake recipe")` (Server executes this).
    *   *Step 2*: `file_create("pancakes.txt", content)` (Delegates to Client to execute).
4.  **Client Update**: Socket events notify the frontend as tasks complete.

---

## 🔌 API & Socket Communication

### 1. Authentication (JWT + OTP)
> All Socket.IO connections require a valid JWT Access Token.

**Flow**:
1.  **Register/Login**: POST `/api/v1/auth/register` or `/api/v1/auth/sign-in` with `email`.
2.  **Verify**: User receives OTP via email. POST `/api/v1/auth/verify-otp`.
3.  **Token**: Server returns `access_token` and `refresh_token`.
4.  **Connect**: Client connects to Socket.IO with `auth: { token: "YOUR_ACCESS_TOKEN" }`.

### 2. Socket.IO Events (`/socket.io`)

#### Client -> Server
| Event | Payload | Description |
| :--- | :--- | :--- |
| `send-user-text-query` | `{ "query": "Hello" }` | Standard text chat. Returns `query-result`. |
| `send-user-voice-query` | `{ "audio": "BASE64...", "mimeType": "audio/webm" }` | Speech-to-Text + Chat. Returns `query-result`. |
| `request-tts` | `{ "text": "Hello world" }` | Stream audio response for given text. |
| `task:result` | `{ "task_id": "...", "result": { ... } }` | **CRITICAL**: Send result of a Client Tool execution back to server. |

#### Server -> Client
| Event | Payload | Description |
| :--- | :--- | :--- |
| `query-result` | `PQHResponse` | **Main AI Response**. Contains the spoken answer and tool plan. |
| `task:execute` | `TaskRecord` | Server telling Client to run a local tool (e.g., `open_app`). |
| `task:status` | `{ "task_id": "...", "status": "completed" }` | Updates on background task progress. |
| `response-tts` | Audio Stream | Binary audio chunks for voice response. |

---

## 🧠 AI Response Schema (`PQHResponse`)

The `query-result` event returns the standard **PQH Format**. Voie agents should use this data to drive the UI and TTS.

```json
{
  "request_id": "req_12345",
  "cognitive_state": {
    "userQuery": "Turn off the wifi",
    "emotion": "neutral",
    "thought_process": "User wants to toggle system setting. Requires client tool.",
    "answer": "I'm checking your network status now.", 
    "answerEnglish": "I'm checking your network status now."
  },
  "requested_tool": ["network_status"]
}
```

> **Spec for Voice Agents**:
> *   **Display**: Show `thought_process` for "thinking" UI.
> *   **Speak**: ALWAYS use `answer` (or `answerEnglish` if distinct) for Text-to-Speech.
> *   **Action**: If `requested_tool` is not empty, show a "Working..." indicator while listening for `task:execute` events.

---

## 🛠️ Tool Registry (Capabilities)

The AI can execute tools on the **Server** (SQH) or delegate them to the **Client**.

### 💻 System Tools (Client-Side)
*Requires the client app (Electron/Python) to handle the `task:execute` event.*
*   `open_app` / `close_app` / `restart_app`: Manage applications.
*   `system_info`: Get CPU/RAM usage.
*   `battery_status`: Check power level.
*   `network_status`: Check connectivity.
*   `clipboard_read` / `clipboard_write`: Clipboard manager.
*   `notification_push`: Send OS notifications.
*   `screenshot_capture`: Take screenshoots.

### 📂 File System (Client-Side)
*   `file_search`: Find files (uses `fd` or recursive search).
*   `file_read` / `file_create` / `file_delete`: Manage file content.
*   `folder_create` / `folder_cleanup`: Directory management.

### 🌐 Web Tools (Server-Side)
*These run automatically on the server.*
*   `web_search`: Google/DuckDuckGo search.
*   `web_scrape`: Extract content from URL.

---

## 🚀 Client Integration Guides

### 1. React / Next.js (Web Client)
*Best for: Chat interface, Dashboard, Server-side tools only.*

```javascript
import io from 'socket.io-client';

const socket = io('https://your-server.com', {
  auth: { token: 'YOUR_JWT_TOKEN' },
  transports: ['websocket']
});

// 1. Send Query
const sendQuery = (text) => {
  socket.emit('send-user-text-query', { query: text });
};

// 2. Handle Immediate Response (PQH)
socket.on('query-result', (data) => {
  const { answer, thought_process } = data.result.cognitive_state;
  playTTS(answer); // Your TTS function
  showThinking(thought_process);
});

// 3. Handle Task Updates (SQH)
socket.on('task:status', (status) => {
  console.log(`Task ${status.task_id} is ${status.status}`);
});
```

### 2. Electron / Desktop (Full Capabilities)
*Best for: System control, File management, App launching.*

You must implement a **Task Executor** to handle `task:execute` events.

```javascript
const { ipcMain, shell, clipboard } = require('electron');

socket.on('task:execute', async (task) => {
  const { task_id, tool, inputs } = task;
  let result = { success: false, error: "Unknown tool" };

  try {
    // === IMPLEMENT CLIENT TOOLS ===
    switch(tool) {
      case 'open_app':
        await shell.openPath(inputs.target);
        result = { success: true, data: { status: "Opened" } };
        break;
        
      case 'clipboard_write':
        clipboard.writeText(inputs.content);
        result = { success: true, data: { copied: true } };
        break;
        
      // ... implement other tools ...
    }
  } catch (err) {
    result = { success: false, error: err.message };
  }

  // === ACKNOWLEDGE RESULT ===
  socket.emit('task:result', {
    user_id: USER_ID,
    task_id: task_id,
    result: result
  });
});
```

### 3. React Native (Mobile)
*Best for: Voice Agent on the go.*

Use `socket.io-client` similar to Web. For `task:execute`, map tools to native modules (e.g., `Linking.openURL`, `Clipboard`, `PushNotificationIOS`).

```javascript
// Example: Handling 'open_app' on mobile
socket.on('task:execute', async (task) => {
  if (task.tool === 'open_app') {
     // On mobile, this might mean opening a deep link
     const supported = await Linking.canOpenURL(task.inputs.target);
     if (supported) {
       await Linking.openURL(task.inputs.target);
       socket.emit('task:result', { ...successPayload });
     }
  }
});
```
