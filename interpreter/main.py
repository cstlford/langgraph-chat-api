import functools
from contextlib import asynccontextmanager
import os


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import matplotlib.pyplot as plt


from schema import CodeRequest, CodeToolResult
from utils import execute_code_async, execute_sql
from config import logger, TEMP_IMAGE_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Code interpreter server starting up")
    yield
    logger.info("Code interpreter server shutting down")
    plt.close("all")


app = FastAPI(
    title="Code Interpreter",
    description="A Python code interpreter with SQL and image support",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/run", response_model=CodeToolResult)
async def run_code(request: CodeRequest):
    """Execute Python code and return results with image URLs and objects"""
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    try:
        logger.info(f"Executing code: {request.code}")
        bound_execute_sql = functools.partial(execute_sql, database=request.database)

        result = await execute_code_async(
            request.code, bound_execute_sql=bound_execute_sql
        )
        logger.info(f"Result: {result}")
        return CodeToolResult(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in run_code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/images/temp/{image_id}.png")
async def serve_image(image_id: str):
    """Serve temporary image files from /tmp"""
    image_path = os.path.join(TEMP_IMAGE_DIR, f"{image_id}.png")
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path, media_type="image/png")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


@app.get("/files/temp/{file_id}.csv")
async def serve_file(file_id: str):
    """Serve temporary CSV files from /tmp"""
    file_path = os.path.join(TEMP_IMAGE_DIR, f"{file_id}.csv")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="text/csv")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
