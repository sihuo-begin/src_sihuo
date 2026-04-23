from fastapi import FastAPI, UploadFile

app = FastAPI()

@app.post("/upload/log")
async def upload_log(file: UploadFile):
    return {"status": "log received"}

@app.post("/upload/repair")
async def upload_repair(file: UploadFile):
    return {"status": "repair excel received"}
