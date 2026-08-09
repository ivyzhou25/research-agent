from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from agent import run_agent

app = FastAPI()


class Query(BaseModel):
    question: str


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Research Agent</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 700px;
                margin: 60px auto;
                padding: 20px;
            }

            h1 {
                text-align: center;
            }

            textarea {
                width: 100%;
                height: 100px;
                padding: 10px;
                font-size: 16px;
                box-sizing: border-box;
            }

            button {
                margin-top: 10px;
                padding: 10px 20px;
                font-size: 16px;
                cursor: pointer;
            }

            #answer {
                margin-top: 30px;
                padding: 20px;
                background: #f5f5f5;
                white-space: pre-wrap;
            }
        </style>
    </head>

    <body>
        <h1>Research Agent</h1>

        <textarea id="question"
            placeholder="What would you like me to research?"></textarea>

        <button onclick="askAgent()">Ask Agent</button>

        <div id="answer"></div>

        <script>
            async function askAgent() {
                const question = document.getElementById("question").value;
                const answer = document.getElementById("answer");

                if (!question.trim()) {
                    answer.textContent = "Please enter a question.";
                    return;
                }

                answer.textContent = "Researching...";

                const response = await fetch("/chat", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        question: question
                    })
                });

                const data = await response.json();

                answer.textContent = data.answer;
            }
        </script>
    </body>
    </html>
    """


@app.post("/chat")
def chat(query: Query):
    answer = run_agent(query.question)
    return {"answer": answer}
