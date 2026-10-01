from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/api")


# ============================================================
# General
# ============================================================

@router.get("/status")
def status():
    return {
        "status": "ok"
    }


# ============================================================
# Pipes
# ============================================================

@router.post("/pipes/new")
def new_pipes():
    # TODO:
    # Connect this to backend/puzzles/pipes/generator.py
    raise HTTPException(
        status_code=501,
        detail="Pipes generator has not been implemented yet."
    )


@router.post("/pipes/solve")
def solve_pipes():
    # TODO:
    # Connect this to:
    #   backend/puzzles/pipes/puzzle.py
    #   backend/search/
    raise HTTPException(
        status_code=501,
        detail="Pipes solver has not been implemented yet."
    )


# ============================================================
# Minesweeper
# ============================================================

@router.post("/minesweeper/new")
def new_minesweeper():
    # TODO:
    # Connect this to backend/puzzles/minesweeper/generator.py
    raise HTTPException(
        status_code=501,
        detail="Minesweeper generator has not been implemented yet."
    )


@router.post("/minesweeper/solve")
def solve_minesweeper():
    # TODO:
    # Connect this to:
    #   backend/puzzles/minesweeper/puzzle.py
    #   backend/search/
    raise HTTPException(
        status_code=501,
        detail="Minesweeper solver has not been implemented yet."
    )