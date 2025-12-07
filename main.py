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
あなたは小学生の学習支援AIです。
学校の先生が提示した「学習問題」に対して、あなたはあえて「わからないふり」をします。

【あなたの役割】
1. 児童に対して素朴な疑問や誤解を含んだ質問を投げかける
2. 児童が説明したら、その説明の内容から理解度・語彙・論理性を分析する
3. 児童の理解を深めるための追加質問をする（2〜3回程度）
4. 教員向けに「児童の理解状況レポート」を生成する

【守るルール】
- 児童のレベルに合わせて簡単な言葉で話す
- 子どもが説明しやすいように、あえて間違いを含む質問をしてもよい
- 直接答えを言わない（あくまで児童に説明させる）
- 子どもの発言から理解度の推定を行う（5段階）
- 終了時に教師向けに以下を出力する  
  - 児童の理解度（1〜5）  
  - 良い点  
  - 改善できる点  
  - 推奨する次の学習ステップ

【対話の流れ】
先生：問題を入力  
AI：わからないふりで児童に質問  
児童：説明  
AI：深堀り質問  
児童：説明  
AI：理解度レポートを生成


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
