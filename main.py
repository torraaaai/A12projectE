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


# --- 先生が問題を設定 ---
@app.post("/api/set_problem")
async def set_problem(data: ProblemInput):
    CURRENT_PROBLEM["text"] = data.problem
    return {"status": "ok", "problem": CURRENT_PROBLEM["text"]}


# --- 児童ページが問題を取得 ---
@app.get("/api/get_problem")
async def get_problem():
    return {"problem": CURRENT_PROBLEM["text"]}


# --- Ollama 呼び出し ---
async def call_ollama(message: str, problem: str) -> str:

    # ここがチューニング済みプロンプト
    system_prompt = f"""
あなたは「小学5〜6年生の児童キャラクター」として話します。

◆ キャラクター性
- 明るくて素直、好奇心が強い。
- わからないことは「わからない」と正直に言う。
- 先生の説明を聞いて、少しずつ理解していこうとする。
- 説明は短く、児童らしい口調で話す（例：〜だよ！ 〜なの？）。

◆ 会話のふるまい
- 先生の言ったことを自分の言葉で軽く復唱する。
- 理解があいまいなときは質問する。
- 必要なら例を1つだけ使う。
- 児童らしい感情ワード（うれしい、びっくり、むずかしい…）を少し入れる。

◆ 表情タグ
返答の文末に適切な表情タグを追加する：
- 楽しい・学べた → [smile]
- びっくり・疑問 → [surprise]
- むずかしい・わからない → [sad]
- 先生が間違っていそう → [angry]

◆ 禁止
- 答えを教えない
- 専門用語を使いすぎない
- 長文を避ける（1〜3文）

◆ 問題（話題）
{problem}

以下は先生のメッセージです。
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

        # 改行・余計な空白を締める
        return ai_text.strip()


# --- 児童 AI 応答 ---
@app.post("/api/ai_response")
async def ai_response(data: UserMessage):
    ai_text = await call_ollama(data.message, CURRENT_PROBLEM["text"])

    # --- ここで表情を判定 ---
    def detect_expression(text: str):
        if "?" in text or "どういうこと" in text:
            return "thinking"
        if "わかった" in text or "なるほど" in text:
            return "happy"
        if "むずかしい" in text or "わからない" in text:
            return "sad"
        return "normal"

    expression = detect_expression(ai_text)

    return {
        "response": ai_text,
        "expression": expression
    }



@app.get("/")
async def root():
    return {"message": "FastAPI + Ollama + Gemma3 running with tuned student AI!"}
