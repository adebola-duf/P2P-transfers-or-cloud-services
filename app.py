from fastapi import FastAPI, File, UploadFile, status, HTTPException, WebSocket, WebSocketDisconnect, status, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from typing import Annotated, Dict
import os

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
upload_dir = "uploads"
os.makedirs(upload_dir, exist_ok=True)


@app.get(path="/")
def home():
    with open("templates/home.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(html_content, status_code=status.HTTP_200_OK)


@app.post(path="/upload-files")
async def upload_files(files: Annotated[list[UploadFile], File(description="Upload 0 or more files")]):
    try:
        if not files:
            return {"message": "No file sent"}

        file_contents = [await file.read() for file in files]
        save_paths = [os.path.join(upload_dir, file.filename)
                      for file in files]

        for i, file_path in enumerate(save_paths):
            with open(file_path, "wb") as f:
                f.write(file_contents[i])

        with open("templates/success_page.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(html_content, status_code=status.HTTP_200_OK)

    except Exception as e:
        with open("templates/no_upload.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def delete_file(filename):
    os.remove(f"uploads/{filename}")
    print(f"deleted {filename}")


@app.get(path="/download/{filename}")
async def download(filename: str, background_tasks: BackgroundTasks):
    # background_tasks.add_task(delete_file, filename)
    return FileResponse(path=f"uploads/{filename}", filename=filename)


@app.get("/stream/{filename}")
def main(filename: str):
    def iterfile():  #
        with open(f"uploads/{filename}", mode="rb") as file_like:  #
            yield from file_like  #

    return StreamingResponse(iterfile())


class ConnectionManager:
    def __init__(self):
        self.id_websocket_dict: Dict[int, WebSocket] = {}
        # this dictionary would store stuffs in this format {"conn0": {sender_id: 9009, "filename": xyz.mp4, "receiver_id": 4244}}
        self.sender_id_file_receiver_id_dict: Dict[str, Dict[str, int | str]] = {
        }

    async def connect(self, websocket: WebSocket, client_id: int):
        await websocket.accept()
        self.id_websocket_dict[client_id] = websocket

    def disconnect(self, websocket: WebSocket):
        client_id_websocket_connection_to_delete = 0
        for client_id, websocket_connection in self.id_websocket_dict.items():
            if websocket_connection == websocket:
                client_id_websocket_connection_to_delete = client_id
        del self.id_websocket_dict[client_id_websocket_connection_to_delete]

    # send a message to yourself
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for client_id, connection in self.id_websocket_dict.items():  # connection here is a websocket object
            await connection.send_text(message)

    async def send_to(self, messsgae: str, receiver_id: int):
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']

        is_video = False
        for extensions in video_extensions:
            if extensions in messsgae:
                json_data = {"download_link": f"/download/{messsgae}",
                             "stream_link": f"/stream/{messsgae}"}
                is_video = True
        if is_video:
            await self.id_websocket_dict[receiver_id].send_json(json_data)
        else:
            await self.id_websocket_dict[receiver_id].send_text(f"/download/{messsgae}")


manager = ConnectionManager()


@app.websocket("/ws/{sender_id}/{receiver_id}")
async def websocket_endpoint(websocket: WebSocket, sender_id: int, receiver_id: int):
    await manager.connect(websocket, sender_id)
    print(manager.id_websocket_dict)
    try:
        while True:
            data = await websocket.receive_text()
            connection_index = 0
            # in a case where the sender sends one file and later sends another one. The first one wont be delteed if receiver isconnects.
            manager.sender_id_file_receiver_id_dict[f"conn{connection_index}"] = {
                "sender_id": sender_id, "filename": data, "receiver_id": receiver_id}
            connection_index += 1
            print(manager.sender_id_file_receiver_id_dict)

            await manager.send_to(data, receiver_id)
    except WebSocketDisconnect:
        # make sure they have closed any tab that is streaming else it won't work.
        # if receiver disconnects is when we want to delete the file.
        deleted_connection = ""
        sender_disconnects = True
        for connection, sender_file_receiver_dict in manager.sender_id_file_receiver_id_dict.items():
            if sender_id == sender_file_receiver_dict["receiver_id"]:
                os.remove(os.path.join(
                    upload_dir, sender_file_receiver_dict["filename"]))
                # i am breaking because each sender would have only one key value pair in the dict. so when we find that one, we should delete it immediately
                deleted_connection = connection
                sender_disconnects = False
                break
        if not sender_disconnects:
            del manager.sender_id_file_receiver_id_dict[deleted_connection]
        manager.disconnect(websocket)


# consider the stuff when you send multiple videos, how do you stream
# , so handle the error that is throwing when client oesn't close the streaming tab befrore disconnecting websocket
