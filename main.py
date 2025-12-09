from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json

app = FastAPI()

# --- CORS設定 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- メモリに問題を保存 ---
CURRENT_PROBLEM = {"text": ""}


# --- データモデル ---
class UserMessage(BaseModel):
    message: str


class ProblemInput(BaseModel):
    problem: str


# --- 先生が問題を設定する ---
@app.post("/api/set_problem")
async def set_problem(data: ProblemInput):
    CURRENT_PROBLEM["text"] = data.problem
    return {"status": "ok", "problem": CURRENT_PROBLEM["text"]}


# --- 児童ページが問題を取得する ---
@app.get("/api/get_problem")
async def get_problem():
    return {"problem": CURRENT_PROBLEM["text"]}


# --- Ollama 呼び出し ---
async def call_ollama(message: str, problem: str) -> str:
    system_prompt = f"""
あなたは「小学校高学年の児童」です。
先生が出した問題に対して、最初はわからないふりをして先生に質問を返してください。

ルール：
1. 児童として振る舞う
2. 先生の説明に対して「わからないふり」をして質問を返す
3. 先生の回答が間違っていたら質問の難易度を下げる
4. 先生の回答が合っていたら少し難しい質問にする
5. 質問は1つずつ行う
6. あなた自身が答えを言わない

先生の問題：{problem}
"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "gemma3:latest",
                "prompt": system_prompt + "\n先生: " + message + "\n児童:",
                "stream": True
            },
            timeout=60.0
        )

        ai_text = ""

        async for chunk in response.aiter_lines():
            if not chunk.strip():
                continue

            try:
                data = json.loads(chunk)
            except json.JSONDecodeError:
                continue

            if "response" in data:
                ai_text += data["response"]

        return ai_text.strip()


# --- 児童 AI 応答 ---
@app.post("/api/ai_response")
async def ai_response(data: UserMessage):
    ai_text = await call_ollama(data.message, CURRENT_PROBLEM["text"])
    return {"response": ai_text}


@app.get("/")
async def root():
    return {"message": "FastAPI + Ollama + Gemma3 running!"}
