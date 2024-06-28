from openai import OpenAI
from fastapi import FastAPI, Form, Request, WebSocket
from typing import Annotated
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

chat_responses = []


@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "chat_responses": chat_responses})


chat_log = [
    {
        'role': 'system',
        'content': 'You are a Python tutor AI, completely dedicated to teach users how to learn Python \
                   from scratch. Please provide clear instructions on Python concepts, best practices \
                   and syntax. Help create a path of learning for users to be able to creat real life, \
                   production ready python applications.'
    }
]


@app.websocket("/ws")
async def chat(websocket: WebSocket):
    await websocket.accept()

    while True: # Will keep the websocket communication with the server open
        user_input = await websocket.receive_text() # Receive text from the client to the server
        chat_log.append({'role': 'user', 'content': user_input})
        chat_responses.append(user_input)

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=chat_log,
                temperature=0.6,
                stream=True
            )

            # If you don't want to stream but send when complete
            # bot_response = response.choices[0].message.content
            # await websocket.send_text(bot_response)  # Send the bot_response back to the client from the server

            # If you want to stream:
            ai_response = ''

            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    ai_response += chunk.choices[0].delta.content
                    await websocket.send_text(chunk.choices[0].delta.content)
            chat_responses.append(ai_response)

        except Exception as e:
            await websocket.send_text(f'Error: {str(e)}')
            break # Will break out of the websocket communication


@app.post("/", response_class=HTMLResponse)
async def chat(request: Request, user_input: Annotated[str, Form()]):
    chat_log.append({'role': 'user', 'content': user_input})
    chat_responses.append(user_input)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=chat_log,
        temperature=0.6
    )

    bot_response = response.choices[0].message.content

    chat_log.append({'role': 'assistant', 'content': bot_response})
    chat_responses.append(bot_response)

    return templates.TemplateResponse("home.html", {'request': request, "chat_responses": chat_responses})


@app.get("/image", response_class=HTMLResponse)
async def image_page(request: Request):
    return templates.TemplateResponse("image.html", {"request": request})


@app.post("/image", response_class=HTMLResponse)
async def create_image(request: Request, user_input: Annotated[str, Form()]):

    response = client.images.generate(
        prompt=user_input,
        n=1,
        size="256x256"
    )

    image_url = response.data[0].url
    return templates.TemplateResponse("image.html", {"request": request, "image_url": image_url})