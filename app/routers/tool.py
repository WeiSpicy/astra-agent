from fastapi import APIRouter
from app.agent.tools import TOOLS, execute_tool
from app.model.tool import ToolRunRequest
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("rag")

@router.get("/list")
def list_tools():
    return {
        "tools": [
            {
                "name": name,
                "description": meta["description"]
            }
            for name, meta in TOOLS.items()
        ]
    }

@router.post("/run")
def tool_run(req: ToolRunRequest):
    result = execute_tool(req.tool, req.args)

    return {
        "tool": req.tool,
        "args": req.args,
        "result": result
    }