import uvicorn

if __name__ == "__main__":
    uvicorn.run("api:app", app_dir="src", host="0.0.0.0", port=8001, reload=False)
