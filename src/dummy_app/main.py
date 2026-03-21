from fastapi import Depends, FastAPI, Header, HTTPException

app = FastAPI(title="Dummy App", description="Target app for verification tests")


def get_bearer_token(authorization: str = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Missing or invalid authorization header"},
        )
    return authorization.removeprefix("Bearer ").strip()


@app.get("/api/v1/users/me")
def get_current_user(token: str = Depends(get_bearer_token)):
    if token == "not-found-user":
        raise HTTPException(
            status_code=404,
            detail={"error": "user_not_found", "message": "User not found"},
        )
    return {"id": "user-001", "email": "demo@example.com", "displayName": "Demo User"}
