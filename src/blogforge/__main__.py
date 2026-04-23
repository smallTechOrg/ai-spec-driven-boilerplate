import uvicorn


def main() -> None:
    from blogforge.config import settings
    uvicorn.run("blogforge.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
