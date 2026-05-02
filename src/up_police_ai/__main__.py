import uvicorn


def main() -> None:
    uvicorn.run(
        "up_police_ai.api:create_app",
        factory=True,
        host="0.0.0.0",
        port=8001,
        reload=False,
    )


if __name__ == "__main__":
    main()
