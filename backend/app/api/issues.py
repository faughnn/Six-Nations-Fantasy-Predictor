from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import httpx

from app.auth import get_current_user
from app.config import get_settings
from app.models.user import User

router = APIRouter()


class CreateIssueRequest(BaseModel):
    type: str = Field(..., pattern="^(bug|feature)$")
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)


class CreateIssueResponse(BaseModel):
    issue_url: str
    issue_number: int


@router.post("", response_model=CreateIssueResponse)
async def create_issue(
    body: CreateIssueRequest,
    user: User = Depends(get_current_user),
):
    settings = get_settings()

    if not settings.github_token or not settings.github_repo:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub integration is not configured",
        )

    label = "bug" if body.type == "bug" else "feature-request"
    issue_body = (
        f"{body.description}\n\n"
        f"---\n"
        f"Submitted by **{user.name}** via the app"
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/repos/{settings.github_repo}/issues",
            headers={
                "Authorization": f"Bearer {settings.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "title": f"[{label}] {body.title}",
                "body": issue_body,
                "labels": [label],
            },
        )

    if resp.status_code != 201:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create GitHub issue",
        )

    data = resp.json()
    return CreateIssueResponse(
        issue_url=data["html_url"],
        issue_number=data["number"],
    )
