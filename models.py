from pydantic import BaseModel, Field


class Scene(BaseModel):
    id: int
    film: str
    title: str
    duration_sec: int
    level: int = Field(ge=1, le=3, description="1 = легко, 2 = средне, 3 = сложно")
    category: str
    video_file: str = Field(description="Filename of the source video inside storage/videos")


class DubResponse(BaseModel):
    job_id: str
    scene_id: int
    output_url: str
