import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, TypedDict

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from logger import get_json_logger

HERE = Path(__file__).parent

logger = get_json_logger(Path(__file__).with_suffix(".log"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

JSON_FILE_PATH = HERE / "flats.json"
if not JSON_FILE_PATH.exists():
    with open(JSON_FILE_PATH, "w") as file:
        json.dump([], file)


class Comment(TypedDict):
    comment: str
    date: str


class FlatInfo(TypedDict):
    furnished: bool


class Flat(TypedDict):
    id: str
    comments: list[Comment]
    photos: list[str]
    flat_info: FlatInfo


def load_flats() -> list[Flat]:
    if not os.path.exists(JSON_FILE_PATH):
        return []
    with open(JSON_FILE_PATH, "r") as file:
        return json.load(file)


def save_flats(flats: list[Flat]):
    with open(JSON_FILE_PATH, "w") as file:
        json.dump(flats, file, indent=4)


def log_new_request(request: Request, **kwargs):
    logger.info(
        {
            "event": "new_request",
            "method": request.method,
            "url": request.url.path,
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            **kwargs,
        }
    )


@app.get("/flats", response_model=List[dict])
def get_flats(request: Request):
    try:
        log_new_request(request)
        flats = load_flats()
        return flats
    except Exception as e:
        logger.exception({"event": "error_get_flats", "error": str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")


class CommentModel(BaseModel):
    comment: str


@app.post("/comment/{flat_id}")
def add_comment(request: Request, flat_id: str, comment: CommentModel):
    try:
        log_new_request(request, flat_id=flat_id, comment=comment.comment)
        flats = load_flats()
        flat = next((flat for flat in flats if flat["id"] == flat_id), None)
        if not flat:
            raise HTTPException(status_code=404, detail="flat not found")

        date_format = "%Y-%m-%d %H:%M:%S"
        new_comment = Comment(
            comment=comment.comment, date=datetime.now().strftime(date_format)
        )

        flat["comments"].append(new_comment)
        save_flats(flats)
        return {"message": "Comment added successfully"}
    except Exception as e:
        logger.exception({"event": "error_add_comment", "error": str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")


def find_file_with_any_extension(dir: str | Path, file_name: str) -> str | None:
    for ext in ["png", "jpg", "jpeg", "webp"]:
        file_path = f"{dir}/{file_name}.{ext}"
        if os.path.exists(file_path):
            return file_path
    return None


@app.get("/images/{image_name}")
def get_image(request: Request, image_name: str):
    try:
        log_new_request(request, image_name=image_name)
        file = find_file_with_any_extension("static", image_name)
        if not file:
            raise HTTPException(status_code=404, detail="Image not found")
        return FileResponse(file)
    except Exception as e:
        logger.exception({"event": "error_get_image", "error": str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    try:
        logger.info({"event": "server_start"})
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.exception({"event": "server_error", "error": str(e)})
        raise e
