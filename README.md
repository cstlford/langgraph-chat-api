## 🧰 Prerequisites & Setup

### 1. Install UV for Package Management

#### macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Create a Virtual Environment

```bash
uv venv
```

### 3. Activate the Environment

#### macOS

```bash
source .venv/bin/activate
```

#### Windows

```bash
.venv\Scripts\activate.ps1
```

### 4. Install Dependencies

```bash
uv sync
```

---

## 🚀 Start the Project

```bash
fastapi dev main.py
```

---

## 🐳 Interpreter Service (Docker)

Build and run the interpreter service Docker image:

```bash
docker build -f interpreter/Dockerfile -t othelia-interpreter .
docker run -p 8001:8001 othelia-interpreter
```
